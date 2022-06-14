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


class Model:
    # create a model object from openapi spec
    def __init__(self, url):
        modelFormat = 'json' if 'json' in url else 'yaml'
        jsonModel = doc_loader(url, format=modelFormat)
        for k,v in jsonModel.items():
            setattr(self, k, v)
        self.name = self.info.get('title', 'Unknown')
        if 'tags' in jsonModel:
           self.tags = [t['name'] for t in self.tags]
        else:
            self.tags = []
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
            defin = self.get_model_component(model, defin['$ref'])
        
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
    
    def get_model_component(self, model, path):
        out = model.components.copy()
        for p in path.split('/'):
            if p in ['#', 'components']:
                continue
            out = out[p]
        return out


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

    def build_request(self, **kwargs):
        url = self.model.session.host + self.path
        if self.hasPathParams:
            url = url.format(**kwargs)
        headers = {}
        