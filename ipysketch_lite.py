from http.server import BaseHTTPRequestHandler, HTTPServer
from IPython.display import HTML, display
import threading
import base64
import io

try:
    from PIL import Image
    import numpy as np

    PIL_INSTALLED = True
except ImportError:
    PIL_INSTALLED = False


class SimpleHTTPRequestHandler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        pass

    def do_POST(self):
        content_length = int(self.headers["Content-Length"])
        post_data = self.rfile.read(content_length)
        message = post_data.decode("utf-8")

        global output
        output = message

        global response_received
        response_received.set()

        self.send_response(200)


def run(server_class=HTTPServer, handler_class=SimpleHTTPRequestHandler, port=5000):
    server_address = ("", port)
    httpd = server_class(server_address, handler_class)
    server_thread = threading.Thread(target=httpd.serve_forever)
    server_thread.start()


class Sketch:
    def __init__(self, width: int = 400, height: int = 300):
        global response_received
        response_received = threading.Event()
        run()
        html_code = """
        <style>
        #toggleFill {
            background-color: #f0f0f0;
            border: 1px solid #999999;
        }

        #toggleFill.active {
            background-color: #ffffff;
            border: 1px solid #000000;
        }
        </style>
        """

        html_code += f"""<canvas id="canvas" width="{width}" height="{height}" style="border: 2px solid black;"></canvas>"""
        html_code += """
        <button id="toggleFill" onclick="toggleFill()">bucket</button>
        <button onclick="clearCanvas()">clear</button>
        <input id="color" type="color" value="#000000"/>
        <script>
        var canvas = document.getElementById("canvas");
        var colorInput = document.getElementById("color");
        var toggleFillButton = document.getElementById("toggleFill");
        var ctx = canvas.getContext("2d");
        ctx.lineWidth = 4;
        ctx.lineJoin = "round";
        var drawing = false;
        var mouse = { x: 0, y: 0 };
        var fillMode = false;
        
        fetch('http://localhost:5000', {
            method: 'POST',
            headers: {
            'Content-Type': 'text/plain',
            },
            body: canvas.toDataURL()
        })

        function toggleFill() {
            fillMode = !fillMode;
            toggleFillButton.classList.toggle("active", fillMode);
        }

        function hexToRgb(hex) {
            return {
            r: parseInt(hex.substring(1, 3), 16),
            g: parseInt(hex.substring(3, 5), 16),
            b: parseInt(hex.substring(5, 7), 16),
            a: 255
            };
        }

        canvas.addEventListener("mousedown", function(e) {
            if (fillMode) {
            floodFill(hexToRgb(colorInput.value), e.offsetX, e.offsetY);
            return;
            }

            mouse = { x: e.offsetX, y: e.offsetY };
            drawing = true;
        });

        canvas.addEventListener("mousemove", function(e) {
            if (drawing) {
            drawLine(ctx, mouse.x, mouse.y, e.offsetX, e.offsetY);
            mouse = { x: e.offsetX, y: e.offsetY };
            }
        });

        canvas.addEventListener("mouseup", function(e) {
            if (drawing) {
            drawLine(ctx, mouse.x, mouse.y, e.offsetX, e.offsetY);
            drawing = false;
            }
            
            fetch('http://localhost:5000', {
                method: 'POST',
                headers: {
                'Content-Type': 'text/plain',
                },
                body: canvas.toDataURL()
            })
        });

        function drawLine(context, x1, y1, x2, y2) {
            ctx.strokeStyle = colorInput.value;
            ctx.beginPath();
            ctx.moveTo(x1, y1);
            ctx.lineTo(x2, y2);
            ctx.closePath();
            ctx.stroke();
        }

        function clearCanvas() {
            ctx.clearRect(0, 0, ctx.canvas.width, ctx.canvas.height);
        }
        
        function floodFill(color, x, y) {
            var imgData = ctx.getImageData(0, 0, canvas.width, canvas.height);
            const { width, height, data } = imgData;
            if (pixelColMatch(x, y, color, data, width)) return;

            const stack = [[x, y]];
            let baseIdx = (width * y + x) * 4;
            const oColor = {
            r: data[baseIdx],
            g: data[baseIdx + 1],
            b: data[baseIdx + 2],
            a: data[baseIdx + 3],
            };

            while (stack.length) {
            var [cx, cy] = stack.pop();
            const move = (dx, dy) => {
                let nx = cx + dx;
                let ny = cy + dy;
                while (
                ny >= 0 &&
                ny < height &&
                pixelColMatch(nx, ny, oColor, data, width)
                ) {
                setPixelCol(nx, ny, color, data, width);
                stack.push([nx, ny]);
                ny += dy;
                }
            };
            move(0, 1);
            move(0, -1);
            move(-1, 0);
            move(1, 0);
            }
            ctx.putImageData(imgData, 0, 0);
        }

        function pixelColMatch(x, y, color, data, width) {
            var baseIdx = (width * y + x) * 4;
            return (
            data[baseIdx] === color.r &&
            data[baseIdx + 1] === color.g &&
            data[baseIdx + 2] === color.b &&
            data[baseIdx + 3] === color.a
            );
        }

        function setPixelCol(x, y, color, data, width) {
            var baseIdx = (width * y + x) * 4;
            data[baseIdx] = color.r & 0xff;
            data[baseIdx + 1] = color.g & 0xff;
            data[baseIdx + 2] = color.b & 0xff;
            data[baseIdx + 3] = color.a & 0xff;
        }
        </script>
        """

        display(HTML(html_code))
        response_received.wait()

    def get_output(self) -> str:
        return output

    def get_output_array(self) -> np.ndarray:
        if PIL_INSTALLED:
            image_data = output.split(",")[1]
            image = Image.open(io.BytesIO(base64.b64decode(image_data)))
            return np.array(image)
        else:
            raise ImportError("PIL (Pillow) and NumPy are required to use this method.")
