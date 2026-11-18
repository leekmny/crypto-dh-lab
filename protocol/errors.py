class ProtocolError(Exception):
    """외부 입력과 통신 실패를 안전하게 보고하는 예외."""

    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code
