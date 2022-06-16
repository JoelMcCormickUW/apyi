from .docparser import Level
import requests


def doc_loader(url, format='json'):
    response = requests.get(url)
    if format == 'json':
        out = response.json()
        
        return out
    elif format == 'yaml':
        lines = response.text.split('\n')
        root = Level('root')
        rows = [Level(line) for line in lines if line.strip()]
        root.find_children(rows)
        return root.to_json()['root']

def get_model_component(model, path):
        out = model._components.copy()
        for p in path.split('/'):
            if p in ['#', 'components']:
                continue
            out = out[p]
        return out

class Model:
    # create a model object from openapi spec
    def __init__(self, url):
        modelFormat = 'json' if 'json' in url else 'yaml'
        jsonModel = doc_loader(url, format=modelFormat)
        print('loaded model')
        for k,v in jsonModel.items():
            setattr(self, k, v)
        self.name = self.info.get('title', 'Unknown')
        if 'tags' in jsonModel:
           self.tags = [t['name'] for t in self.tags]
        else:
            self.tags = []
        self._op_lookup = {}
        self._components = self.components
        self.components = Component(self, 'components', self._components)
        self.load_operations()
        
    def __getattr__(self, __name: str):
        if __name in self._op_lookup:
            return self._op_lookup[__name]
        elif __name in self.tags:
            return Tag(self, __name)
        else:
            raise KeyError(f'{__name} not found in {self.name}')   

    def __repr__(self):
        return f'<API Model: {self.name}>'

    def load_operations(self):
        out = []
        for endpoint, operations in self.paths.items():
            for method, defin in operations.items():
                out.append(Operation(self, endpoint, {method: defin}))
        
        ids = [o.operationId for o in out]
        self._op_lookup = dict(zip(ids, out))
        self._ops = out

    def get_component(self, ref):
        found = self.components
        for p in ref.split('/'):
            if p in ['#', 'components']:
                continue
            found = getattr(found, p)
        return found


class Tag:
    def __init__(self, model, name):
        self.model = model
        self._ops = [i.operationId for i in model._ops if name in i.tags]
    
    def __getattr__(self, __name):
        if __name in self._ops:
            return getattr(self.model, __name)
    
    def list_ops(self):
        return [getattr(self.model, op) for op in self._ops]




class Parameter:
    def __init__(self, model:Model, defin):
        if '$ref' in defin:
            defin = get_model_component(model, defin['$ref'])
        
        self._defin = defin.copy()
        self.in_ = self._defin.pop('in') if 'in' in self._defin else None

        self.model = model
        for k, v in self._defin.items():
            if v in ['true', 'false']:
                v = bool(v)
            setattr(self, k, v)

    def __repr__(self):
        try:
            return f"<Definition - {self.in_} parameter: {self.name}>"
        except AttributeError:
            return f"<Definition - parameter of unknown type>"
    
    

class Body:
    def __init__(self, model:Model, defin):
        self.description = defin.get('description', '')
        self.contentType = list(defin['content'].keys())[0]
        self.required = defin.get('required', 'false') == 'true'
        self._raw = defin.copy()
        self.schema = Component(model, 'schema', defin['content'][self.contentType]['schema'])

    @property
    def template(self):
        return self.schema.build_template()



class Component:
    def __init__(self, model:Model, name:str, defin:dict):
        self._name = name
        self._model = model
        if isinstance(defin, str):
            key, val = defin.replace('"', '').split(':')
            defin = {key.strip(): val.strip()}
        try:
            for k,v in defin.items():
                if k == 'allOf':
                    v = self.concat(v)
                    continue
                if isinstance(v, dict):
                    if '$ref' in v:
                        v = get_model_component(self._model, v['$ref'])
                    setattr(self, k, Component(self._model, k, v))
                else:
                    setattr(self, k, v)
        except AttributeError:
            print(defin)
            raise

    def __getattr__(self, name):
        if 'items' in self.__dict__:
            return getattr(self.items, name)
        elif 'properties' in self.__dict__:
            return getattr(self.properties, name)
        else:
            raise AttributeError
        
    

    def build_template(self, explain=False):
        type_ = self.type if hasattr(self, 'type') else 'object'
        match type_:

            case 'object':
                if not hasattr(self, 'properties'):
                    return {}
                out = {k:v.build_template(explain=explain) for k,v in self.properties.__dict__.items() if not k.startswith('_')}
            
            case 'array':
                if not hasattr(self, 'items'):
                    return []
                out = [self.items.build_template(explain=explain)]
            

            case 'string' if hasattr(self, 'enum'):
                out = self.enum[0]
            
            case 'string':
                out = 'placeholder'
            
            case 'integer' if hasattr(self, 'default'):
                out = self.default
            
            case 'integer' if hasattr(self, 'minimum'):
                out = self.minimum

            case 'integer':
                out = 0

            case 'boolean':
                out = False
            
            case 'float' if hasattr(self, 'default'):
                out = self.default

            case 'float' if hasattr(self, 'minimum'):
                out = self.minimum
                    
            case 'float':
                out = 0.0

            case 'number':
                out = 0

            case _:
                print(self)
                raise ValueError(f'Unknown type: {type_}')

        if type_ not in ['object', 'array'] and explain:
            if hasattr(self, 'description'):
                out = self.description

        return out
                

    def concat(self, array):
    
        for i in array:
            if '$ref' in i:
                try:
                    i = get_model_component(self._model, i['$ref'])
                except TypeError:
                    ref, path = i.replace('"', '').split(':')
                    i = get_model_component(self._model, path.strip())
            holding = Component(self._model, self._name, i)
            for k,v in holding.__dict__.items():
                if k in self.__dict__ and isinstance(self.__dict__[k], dict):
                    self.__dict__[k].update(v)
                if k in self.__dict__ and isinstance(self.__dict__[k], Component):
                    self.__dict__[k].__dict__.update(v.__dict__)
                
                elif k not in self.__dict__:
                    setattr(self, k, v)

 

    def __repr__(self):
        if 'description' in self.__dict__:
            return f"<{self._name}: {self.description}>"
        else:
            return f'<{self._name}>'

    


class Operation:
    def __init__(self, model:Model, endpoint:str, definition:dict):
        self._model = model
        self.path = endpoint
        self._raw = definition.copy()
        self.method = list(self._raw.keys())[0]
        stage = self._raw.copy().pop(self.method)
        for k, v in stage.items():
            setattr(self, k, v)
        if hasattr(self, 'parameters'):
            self.parameters = [Parameter(model, p) for p in self.parameters]
        if not hasattr(self, 'operationId'):
            dumbname = self.path
            opname = [i for i in dumbname.split('/') if i not in ['v3', 'sd', 'sp'] and '{' not in i]
            self.operationId = self.method + "_".join(opname)

        if hasattr(self, 'requestBody'):
            self.requestBody = Body(model, self.requestBody)
    
    def __repr__(self):
        return f'<HTTP {self._model.info["title"]} Operation: {self.operationId}>'

    @property
    def headers(self):
        return [p for p in self.parameters if p.in_ == 'header']
    
    @property
    def required(self):
        return [p for p in self.parameters if hasattr(p, 'required') and p.required]

    @property
    def hasPathParams(self):
        return any(p.in_ == 'path' for p in self.parameters)

    @property
    def about(self):
        if hasattr(self, 'description'):
            return self.description
        return self.summary




    
        


