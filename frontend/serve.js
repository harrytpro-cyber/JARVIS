const http = require("http");
const fs = require("fs");
const path = require("path");

const PORT = 3000;
const DIR = __dirname;

const TYPES = {
  ".html": "text/html",
  ".css": "text/css",
  ".js": "application/javascript",
  ".json": "application/json",
  ".svg": "image/svg+xml",
  ".png": "image/png",
};

http.createServer((req, res) => {
  let filePath = path.join(DIR, req.url === "/" ? "demo.html" : req.url);
  const ext = path.extname(filePath);
  const type = TYPES[ext] || "text/plain";

  fs.readFile(filePath, (err, data) => {
    if (err) {
      res.writeHead(404);
      res.end("Not found");
      return;
    }
    res.writeHead(200, { "Content-Type": type });
    res.end(data);
  });
}).listen(PORT, () => console.log(`JARVIS demo → http://localhost:${PORT}`));
