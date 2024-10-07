# ponguu


## Usage
```bash
pip install git+https://github.com/hoffmben/ponguu.git
```

```python
from pongu.connection import PongU
connection = PongU('<nick>', '<username>', '<password>', '<host>')
for i in range(1):
    connection.publish_messages(f"🌊 hey {i}")

message = connection.collect_messages()
print(message)
```
