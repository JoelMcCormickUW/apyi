import math
import re

from zmq import has

# regex to capture indentation: start of string, match spaces 0+ times, capture '- ' if exists.  
# array values with inconsistent indentation and sneaky carriage returns makes using line - line.strip() to count indentation a bad choice
INDENTREGEX = re.compile(r'^[ ]*(?:\- )?')
# check for a series of non-whitespace characters followed by :
KEYREGEX = re.compile(r'^[A-Za-z0-9$]*:')
MULTILINEINDICATORS = ['|-', '>', '>-']

def check_indent(line):
    # match compiled regex against line, length of group string == indentation level
    return len(INDENTREGEX.match(line).group())

def hasKey(line):
    return KEYREGEX.match(line) is not None

def errorPrinter(method):
    def wrapper(*args,**kwargs):
        try:
            return method(*args, **kwargs)
        except Exception as e:
            print(args[0])
            raise
    return wrapper

class Level:
    # class to store indentation level
    def __init__(self, line:str):
        # find own indentation level
        self.level = check_indent(line)
        # store future sub-levels
        self.sub_lines:list = []
        # strip whitespace
        self.raw:str = line.strip()
        # identify line types that require special handling
        self.isArrayValue = self.raw.startswith('- ')
        self.isMultiline = False
        # who needs consistency? 
        
        for indicator in MULTILINEINDICATORS:
            if self.raw.endswith(indicator):
                self.isMultiline = True
                break
        # you know what? let's just assume descriptions are multi-line.
        if self.raw.startswith('description:'):
            self.isMultiline = True
            self.check_description()

        
    def __repr__(self):
        return f'<Level {self.level}>\n\tnumChildren: {len(self.sub_lines)}\n\tlevel: {self.level}\n\traw:\n\t\t{self.raw}'

    @property
    def text(self):
        # return text of line sans structural characters
        raw = self.raw
        match raw:
            # array values
            case _ if self.isArrayValue:
                return raw[2:]
            # parent keys
            case _ if raw.endswith(':'):
                return raw[:-1]
            # multi-line text (primarily...exclusively?...descriptions)
            case _ if self.isMultiline:
                return raw[:-4]
            # single-line key-value pairs
            case _ :
                return raw

    @property
    def out(self):
        # return line as correct object type
        text = self.text
        keyed = hasKey(text)
        if keyed:
            k,v = text.split(':', 1)
            # this is redundant, but doesn't hurt to check
            if v:
                v = v.strip().replace('"', '')
                v = v.replace("'", '')
                return {k:v}
        return text
    
    def check_description(self):
        if self.raw.endswith('|-'):
            # screw it, i'm done with the inconsistency.
            self.raw = 'description: |-'
            return
        else:
            leading = " " * (self.level + 1)
            k,v = self.raw.split(':',1)
            self.raw = 'description: |-'
            self.sub_lines.insert(0, Level(leading + v))


    def find_children(self, lines):
        """ Creates nested object structure based on indentation level

        Args:
            lines (list): list of Level objects
                ex: 
                    # load source
                    with open('source.txt', 'r') as f:
                        doc = f.readlines()
                    # split by lines
                    rows =  doc.split('\\n')
                    # create a Level object to contain rows
                    root = Level('arbitrary')
                    # create Level objects for each row if it isn't empty
                    lines = [Level(i) for i in lines if i.strip()] 
                    # give lines to container's find_children
                    root.find_children(lines)
                    # profit
                    final = root.to_json()['arbitrary']

        """
        # get level of starting line        
        currentLevel = lines[0].level
        while lines:
            # remove next line from list
            this = lines.pop(0)
            match this:
                # if row is not indented more, belongs to same sub_line group
                case _ if this.level == currentLevel:
                    self.sub_lines.append(this)
                # if row is indented more, put the line back and pass list to the last sub-line
                case _ if this.level > currentLevel:
                    lines.insert(0, this)
                    self.sub_lines[-1].find_children(lines) # blocks this object until lines return to this level
                # if row is equal or less than object's level, line is not sub-line.  Put it back and return
                case _ if this.level <= self.level:
                    lines.insert(0, this)
                    return # parent object becomes unblocked

    def eat_the_children_first(self):
        # concatenates sublines into a single string
        if not self.sub_lines:
            for i in MULTILINEINDICATORS:
                if self.raw.endswith(i):
                    leading = " " * (self.level + 1)
                    self.sub_lines.append(Level(leading+'None'))
                    
            return
        cookingPot = ''
        for child in self.sub_lines:  # open jar of 1 - 3 children
            cookingPot += child.raw + ' '# slowly stir in raw children
        cooked = cookingPot.strip() # when internal temp reaches desired rarity, remove from pot and trim excess grisle
        garnish = ' '*(self.level+1) # proper presentation is essential
        plate = Level(garnish+cooked) # new dinnerware for every meal might seem like overkill, but you can buy them in bulk and unlike dishwashers, you don't have to give them healthcare and PTO
        self.sub_lines = [plate] # bon appetit

    def to_json(self):
        # recursively convert self and sub-lines to python data structures
        # if this level was a multi-line string, concat sublines first
      
        if self.isMultiline:
            self.eat_the_children_first()
     
        # decide what to do based on number of nested objects
        children = len(self.sub_lines)
        
        # if no sublines, return own value
        # otherwise create an array or dict of children 
        match children:

            case 1 if self.sub_lines[0].isArrayValue:
                return {self.out: [self.sub_lines[0].to_json()]}

            case 1:
                return {self.out: self.sub_lines[0].to_json()}
            
            case _ if children > 1 and self.sub_lines[0].isArrayValue:
                out = []
                for row in self.sub_lines:
                    # catch indentation anomolies in arrays
                    if row.isArrayValue:
                        out.append(row.to_json())
                    else:
                        out[-1].update(row.to_json())
                return {self.out: out}
            
            case _ if children > 1 and not self.sub_lines[0].isArrayValue:
                out = {self.out:{}}
                
                for row in self.sub_lines:
                    try:
                        out[self.out].update(row.to_json())
                    except:
                        '''
                        print('raw')
                        print(self.raw)
                        print('out:',out, self.isMultiline, self.isArrayValue)
                        print('clean')
                        print(self.out)
                        print('rows')
                        print(row.raw)
                        print(row.out)
                        print(row.isMultiline, row.isArrayValue)
                        print(row.sub_lines)
                        '''
                        continue
                return out
            
            case _:
                return self.out
                