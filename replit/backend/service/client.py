from mcp import Client

class MCPClient:
    def __init__(self):
        self.client = Client()

    def connect(self):
        self.client.connect()

    def disconnect(self):
        self.client.disconnect()
        
    def get_response(self, prompt: str) -> str:
        return self.client.get_response(prompt)

    def get_response_async(self, prompt: str) -> str:
        return self.client.get_response_async(prompt)

    def get_response_stream(self, prompt: str) -> str:
        return self.client.get_response_stream(prompt)

    def get_response_stream_async(self, prompt: str) -> str:
        return self.client.get_response_stream_async(prompt)