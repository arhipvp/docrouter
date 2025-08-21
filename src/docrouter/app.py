    from fastapi import FastAPI, UploadFile, File
    from fastapi.responses import JSONResponse, HTMLResponse
    from pathlib import Path
    from .pipeline import process_upload
    from .storage import Paths

    app = FastAPI(title="DocRouter Family")

    @app.get("/")
    async def index():
        return HTMLResponse("""
<html><body>
<h3>DocRouter upload (family)</h3>
<form action='/api/upload' method='post' enctype='multipart/form-data'>
  <input type='file' name='files' multiple>
  <button type='submit'>Upload</button>
</form>
</body></html>
""")

    @app.post("/api/upload")
    async def api_upload(files: list[UploadFile] = File(...)):
        saved = []
        for f in files:
            dest = Paths.inbox() / f.filename
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_bytes(await f.read())
            saved.append(dest)
        artifacts = await process_upload([Path(p) for p in saved])
        return JSONResponse(artifacts)

    def main():
        import uvicorn
        uvicorn.run(app, host="0.0.0.0", port=8080)

    if __name__ == "__main__":
        main()
