from fastapi import Depends, FastAPI
from fastapi.security import OAuth2PasswordRequestForm
from groups import router as groups_router
from pages import router as pages_router
from users import router as users_router

URL_API_PREFIX: str = "/ucsschool/bff-users"

app = FastAPI(
    title="UCS@school Users-UI Backend",
    docs_url=f"{URL_API_PREFIX}/docs",
    redoc_url=f"{URL_API_PREFIX}/redoc",
    openapi_url=f"{URL_API_PREFIX}/openapi.json",
)

app = FastAPI(
    title="UCS@school Users-UI Backend",
    version="0.0.0",
)


@app.post("/token", tags=["auth"])
async def login(form_data: OAuth2PasswordRequestForm = Depends()) -> dict[str, str]:
    return {"access_token": "TOKEN"}


app.include_router(users_router)
app.include_router(groups_router)
app.include_router(pages_router)
