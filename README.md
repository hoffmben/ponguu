# ponguu


## Usage
```python
connection = PongU('<nick>', '<username>', '<password>', '<host>')
for i in range(1):
    connection.publish_messages(f"🌊 hey {i}")

message = connection.collect_messages()
print(message)
```