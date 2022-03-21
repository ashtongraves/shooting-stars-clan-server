import jwt

class MiddlewareComponent:
    def validate_JWT(self, req, resp):
        token = req.auth
        jwt.decode()