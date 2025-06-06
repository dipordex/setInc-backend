PHONE_CODE_OPERATION_DESCRIPTION = """
**Conditions**:
- The endpoint allows requests from any user, without requiring prior authentication.

**Input Fields**:
- `phone_number`: The phone number must be valid and conform to the expected format.

**Responses**:
- `200 OK`: Returns a success message indicating the verification code is sent.
- `400 Bad Request`: Returns an error message if the phone number format is invalid.
"""

PHONE_NUMBER_OPERATION_DESCRIPTION = """
Verifies the provided verification code against the phone number submitted by the user. This endpoint is essential for confirming that the user possesses the phone number they claim.

**Workflow**:
1. The user submits their phone number and the received verification code.
2. The system checks if the submitted verification code matches the one stored in the database for the given phone number.
3. If the codes match, the phone number is marked as verified, and the verification code is deleted from the database.
4. The API then checks if a user account associated with the phone number exists.
   - If an account exists, the API returns authentication tokens for the user, indicating whether they are a new user.
   - If no account exists, a new user account is created using the phone number, and authentication tokens are generated and returned.

**Input Fields**:
- `phone_number`: The phone number must be valid and conform to the expected format.
- `verification_code`: The verification code received by the user. Must match the length defined in the system constants and contain only digits.

**Success Response**:
- Returns authentication tokens (`access` and `refresh` tokens) and a flag indicating whether the user is new (`new_user`).

**Failure Responses**:
- `400 Bad Request`: Returned if the submitted verification code does not match the expected format, is incorrect, or if the phone number does not have an associated verification code.
- `404 Not Found`: Returned if the submitted phone number is not found in the system.

Use this endpoint with caution, as it involves sensitive operations related to user authentication and verification.
"""