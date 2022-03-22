import os
ERROR_MSG_DATA_VALIDATION_FAIL = 'Failed data validation. This request has been flagged.'
ERROR_MSG_AUTHORIZATION_FAIL = 'Authorization failed.'
VALID_WORLDS = {n for n in range(301, 581)}
VALID_LOCATIONS = set(range(14))
PORT = int(os.environ['PORT'])
DATABASE_PATH = os.environ['DATABASE']