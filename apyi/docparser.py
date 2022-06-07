import math
import re

# regex to capture indentation: start of string, match spaces 0+ times, capture '- ' if exists.  
# array values with inconsistent indentation and sneaky carriage returns makes using line - line.strip() to count indentation a bad choice
INDENTREGEX = re.compile(r'^[ ]*(?:\- )?')
# check for a series of non-whitespace characters followed by :
KEYREGEX = re.compile(r'^[A-Za-z0-9$]*:')

def check_indent(line):
    # match compiled regex against line, length of group string == indentation level
    return len(INDENTREGEX.match(line).group())

def hasKey(line):
    return KEYREGEX.match(line) is not None

class Level:
    # class to store indentation level
    def __init__(self, line):
        # find own indentation level
        self.level = check_indent(line)
        # store future sub-levels
        self.sub_lines = []
        # strip whitespace
        self.raw = line.strip()
        # identify line types that require special handling
        self.isArrayValue = self.raw.startswith('- ')
        self.isMultiline = self.raw.endswith('|-')
        
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
        kidsMeal = '' # small portions, but super tender
        for child in self.sub_lines:  # open jar of 1 - 3 children
            kidsMeal += child.raw + ' ' #stir separately until thouroughly mixed
        self.sub_lines = [self.sub_lines[0]]  # combine with the main dish
        self.sub_lines[0].raw = kidsMeal.strip() # ...lick the spoon? (get rid of the trailing space)

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
                        print(self.raw, self.out, children, self.sub_lines[0].raw)
                        raise
                return out
            
            case _:
                return self.out
                