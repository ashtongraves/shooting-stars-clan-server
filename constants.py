import os
ERROR_MSG_DATA_VALIDATION_FAIL = 'Failed data validation. This request has been flagged.'
ERROR_MSG_AUTHORIZATION_FAIL = 'Authorization failed.'
ERROR_MSG_AUTHORIZATION_FAIL_SUBMIT = 'Only authorized users may send in data.'
VALID_WORLDS = {n for n in range(301, 581)}
VALID_LOCATIONS = set(range(14))
PORT = int(os.environ['PORT'])
DATABASE_PATH = os.environ['DATABASE']
PASSWORD_ENABLED = os.environ['PASSWORD'].lower() in ("yes", "true", "t", "1")