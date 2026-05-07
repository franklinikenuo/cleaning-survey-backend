from fastapi import FastAPI

app = FastAPI()

@app.get("/")
def root():
    return {"message": "Cleaning Survey API is running"}
