# apyi
## Version 0.0.0

Creates model objects from openapi specifications. 

## Installation

requires:
- requests


## Example Usage


```python
from apyi.components import Model

# generate model
model = Model('https://example.com/api/models/this.yaml')

# operations can be accessed as attributes through their operationId
getUser = model.getUser

# or through their tag
model.Users.getUser

# tags can also be used to get operations using that tag
userOps = model.Users.list_ops()  # returns a list of operation objects


# Operations house descriptive information and Parameter objects, $ref components are loaded from the model
print(getUser.about)
prams = getUser.parameters # list of Parameter objects

required = getUser.required # list excluding optional parameters


# Parameters 
username = prams[0]
username.schema # schema dict
username.required # bool 
username.description # string

```


# <kbd>module</kbd> `apyi.components`
<a href="..\..\apyi\components.py#L19"><img align="right" style="float:right;" src="https://img.shields.io/badge/-source-cccccc?style=flat-square"></a>

## <kbd>class</kbd> `Model`




<a href="..\..\apyi\components.py#21"><img align="right" style="float:right;" src="https://img.shields.io/badge/-source-cccccc?style=flat-square"></a>

### <kbd>method</kbd> `Model.__init__`

```python
Model(
    url: str
)
```
Model gets the content of the given URL and parses the structure to create a Model instance which houses Operations for the API.  Currently supports parsing openapi specifications in .json and .yaml formats.

Operations can be accessed as attributes of the model directly.  Tags accessed as model attributes create Tag objects that generate lists of Operations. 





<a href="..\..\apyi\components.py#L53"><img align="right" style="float:right;" src="https://img.shields.io/badge/-source-cccccc?style=flat-square"></a>

## <kbd>class</kbd> `Tag`
<a href="..\..\apyi\components.py#54"><img align="right" style="float:right;" src="https://img.shields.io/badge/-source-cccccc?style=flat-square"></a>

### <kbd>method</kbd> `Tag.__init__`



```python
Tag(
    model: Model,
    name: str
)
```
Instantiated by the __getattr__ method of the Model class. 
**Args:**
- <b>`model`</b> (Model): Parent model object
- <b>`name`</b> (str): Tag

<a href="..\..\apyi\components.py#54"><img align="right" style="float:right;" src="https://img.shields.io/badge/-source-cccccc?style=flat-square"></a>

### <kbd>method</kbd> `Tag.list_ops`
**Returns:**
- <b>`list`</b> (Operation): List of operations tagged with Tag's name.


<a href="..\..\apyi\components.py#L68"><img align="right" style="float:right;" src="https://img.shields.io/badge/-source-cccccc?style=flat-square"></a>

## <kbd>class</kbd> `Parameter`
```python
Tag(
    model: Model,
)
```
Houses operation parameters.  Retrieves $ref parameters from parent Model.  Attributes created for name, description, schema, etc. 

<a href="..\..\apyi\components.py#L97"><img align="right" style="float:right;" src="https://img.shields.io/badge/-source-cccccc?style=flat-square"></a>

## <kbd>class</kbd> `Operation`
```python
Operation(
    model: Model,
    endpoint: str,
    definition: dict
)
```
Contains operation data and Parameter objects. 

**Args:**
- <b>`model`</b> (Model): Parent model object
- <b>`endpoint`</b> (str): Endpoint (path) of operation
- <b>`definition`</b> (dict): Operation definition from openapi specification

#### <kbd>attribute</kbd> `Tag.path`
(str): endpoint path to append to server url

#### <kbd>attribute</kbd> `Tag.method`
(str): HTTP method of operation (lowercase)

#### <kbd>property</kbd> `Tag.headers`
**Returns:**
- <b>`list`</b> (Parameter): List of parameters used in HTTP headers.

#### <kbd>property</kbd> `Tag.required`
**Returns:**
- <b>`list`</b> (Parameter): List of parameters flagged as required.

#### <kbd>property</kbd> `Tag.about`
**Returns:**
- <b>`str`</b> Description or summary of operation.

# <kbd>module</kbd> `apyi.docparser`
<a href="..\..\apyi\docparser.py"><img align="right" style="float:right;" src="https://img.shields.io/badge/-source-cccccc?style=flat-square"></a>


**Globals:**
- INDENTREGEX
- KEYREGEX

**Functions:**
- check_indent(line)
- hasKey(line)
## <kbd>class</kbd> `Level`
<a href="..\..\apyi\docparser.py#L17"><img align="right" style="float:right;" src="https://img.shields.io/badge/-source-cccccc?style=flat-square"></a>

### <kbd>method</kbd> `Level.__init__`

```python
Level(
    line: str,
)
```

Used to parse yaml indented text structure and convert to json. 

```python
raw = requests.get('someurl.com/withan/openapi/model.yaml').text
split = raw.split('\n')
root = Level('root')
lines = [Level(line) for line in split if line.strip()]
root.find_children(lines)

out = root.to_json()['root']

```