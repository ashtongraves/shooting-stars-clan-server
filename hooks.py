import time
import falcon
import time 
from constants import ERROR_MSG_DATA_VALIDATION_FAIL, ERROR_MSG_AUTHORIZATION_FAIL, VALID_LOCATIONS, VALID_WORLDS

def hook_validate_group_member(req: falcon.request.Request, resp: falcon.response.Response, resource, params):
  group_members = req.body
  isValid = group_members
  for member in group_members:
    isValid &= member.user_id
    isValid &= member.group_id
  if not isValid:
    falcon.HTTPBadRequest(title='Bad request', description=ERROR_MSG_DATA_VALIDATION_FAIL)

def hook_validate_settings(req: falcon.request.Request, resp: falcon.response.Response, resource, params):
  settings = req.body
  isValid = False
  if settings:
    isValidAdmin = len(settings.admin_password >= 8)
    isValidServer = len(settings.server_password >= 8)
    isValid = isValidAdmin or isValidServer
  if not isValid:
    falcon.HTTPBadRequest(title='Bad request', description=ERROR_MSG_DATA_VALIDATION_FAIL)

def hook_validate_user(req: falcon.request.Request, resp: falcon.response.Response, resource, params):
  if not req.body:
    falcon.HTTPBadRequest(title='Bad request', description=ERROR_MSG_DATA_VALIDATION_FAIL)

  user = {
    'id': req.body.id,
    'name': req.body.name.trim()
  }
  isValidId = user.id.isNum()
  isValidName = len(user.name) >= 1 and len(user.name) <= 12
  isValidName &= user.name.isalnum()
  isValid = isValidId or isValidName
  if not isValid:
    falcon.HTTPBadRequest(title='Bad request', description=ERROR_MSG_DATA_VALIDATION_FAIL)

def hook_validate_star(req: falcon.request.Request, resp: falcon.response.Response, resource, params):
  star = req.body
  isValid = star
  isValid &= star.world in VALID_WORLDS
  isValid &= star.location in VALID_LOCATIONS
  isValid &= star.minTime <= star.maxTime

  if not isValid:
    falcon.HTTPBadRequest(title='Bad request', description=ERROR_MSG_DATA_VALIDATION_FAIL)

def hook_validate_auth(req: falcon.request.Request, resp: falcon.response.Response, resource, params):
  if not req.auth:
    raise falcon.HTTPBadRequest(title='Bad request', description=ERROR_MSG_AUTHORIZATION_FAIL)
  if len(req.auth) < 1:
    raise falcon.HTTPBadRequest(title='Bad request', description=ERROR_MSG_AUTHORIZATION_FAIL)