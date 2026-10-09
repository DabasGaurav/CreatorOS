from pydantic import BaseModel


class RerankerOutput(BaseModel):
    why_now: str
    why_you: str


class ContentPackage(BaseModel):
    hook: str
    script: str
    storyboard: str
    caption: str
    cta: str
