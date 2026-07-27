class AppException(Exception):
    def __init__(self, code: str, message: str, status_code: int = 400):
        self.code = code
        self.message = message
        self.status_code = status_code


class NotFoundException(AppException):
    def __init__(self, message="资源不存在"):
        super().__init__("not_found", message, 404)


class LLMException(AppException):
    def __init__(self, message="LLM 调用失败"):
        super().__init__("llm_error", message, 502)
