import asyncio
import ssl
import typing

import h2.config
import h2.connection
import h2.events

from httpx import AsyncioBackend, BaseStream, Request, TimeoutConfig


class MockHTTP2Backend(AsyncioBackend):
    def __init__(self, app):
        self.app = app
        self.server = None

    async def connect(
        self,
        hostname: str,
        port: int,
        ssl_context: typing.Optional[ssl.SSLContext],
        timeout: TimeoutConfig,
    ) -> BaseStream:
        self.server = MockHTTP2Server(self.app)
        return self.server


class MockHTTP2Server(BaseStream):
    def __init__(self, app):
        config = h2.config.H2Configuration(client_side=False)
        self.conn = h2.connection.H2Connection(config=config)
        self.app = app
        self.buffer = b""
        self.requests = {}
        self.close_connection = False
        self.wait_events = {}

    # Stream interface

    def get_http_version(self) -> str:
        return "HTTP/2"

    async def read(self, n, timeout, flag=None) -> bytes:
        await asyncio.sleep(0)
        send, self.buffer = self.buffer[:n], self.buffer[n:]
        return send

    def write_no_block(self, data: bytes) -> None:
        events = self.conn.receive_data(data)
        self.buffer += self.conn.data_to_send()
        for event in events:
            if isinstance(event, h2.events.RequestReceived):
                self.request_received(event.headers, event.stream_id)
            elif isinstance(event, h2.events.DataReceived):
                self.receive_data(
                    event.data, event.stream_id, event.flow_controlled_length
                )
            elif isinstance(event, h2.events.StreamEnded):
                self.stream_complete(event.stream_id)
            elif isinstance(event, h2.events.WindowUpdated):
                self.window_updated(event.stream_id)

    async def write(self, data: bytes, timeout) -> None:
        self.write_no_block(data)

    async def close(self) -> None:
        pass

    def is_connection_dropped(self) -> bool:
        return self.close_connection

    # Server implementation

    def window_updated(self, stream_id):
        if stream_id in self.wait_events:
            self.wait_events[stream_id].set()

    def request_received(self, headers, stream_id):
        """
        Handler for when the initial part of the HTTP request is received.
        """
        if stream_id not in self.requests:
            self.requests[stream_id] = []
        self.requests[stream_id].append({"headers": headers, "data": b""})

    def receive_data(self, data, stream_id, flow_controlled_length):
        """
        Handler for when a data part of the HTTP request is received.
        """
        self.conn.acknowledge_received_data(flow_controlled_length, stream_id)
        self.requests[stream_id][-1]["data"] += data

    def stream_complete(self, stream_id):
        """
        Handler for when the HTTP request is completed.
        """
        request = self.requests[stream_id].pop(0)
        if not self.requests[stream_id]:
            del self.requests[stream_id]

        headers_dict = dict(request["headers"])

        method = headers_dict[b":method"].decode("ascii")
        url = "%s://%s%s" % (
            headers_dict[b":scheme"].decode("ascii"),
            headers_dict[b":authority"].decode("ascii"),
            headers_dict[b":path"].decode("ascii"),
        )
        headers = [(k, v) for k, v in request["headers"] if not k.startswith(b":")]
        data = request["data"]

        # Call out to the app.
        request = Request(method, url, headers=headers, data=data)
        response = self.app(request)

        # Write the response to the buffer.
        status_code_bytes = str(response.status_code).encode("ascii")
        response_headers = [(b":status", status_code_bytes)] + response.headers.raw

        self.conn.send_headers(stream_id, response_headers)
        asyncio.ensure_future(self.send_data(response.content, stream_id))

    async def send_data(self, data, stream_id):
        window_size = self.conn.local_flow_control_window(stream_id)
        max_frame_size = self.conn.max_outbound_frame_size
        chunk_size = min(len(data), window_size, max_frame_size)

        for idx in range(0, len(data), chunk_size):
            left_window_size = self.conn.local_flow_control_window(stream_id)
            if left_window_size < chunk_size:
                self.wait_events[stream_id] = asyncio.Event()
                await self.wait_events[stream_id].wait()

            chunk = data[idx : idx + chunk_size]
            self.conn.send_data(stream_id, chunk)
            self.buffer += self.conn.data_to_send()

        self.conn.end_stream(stream_id)
