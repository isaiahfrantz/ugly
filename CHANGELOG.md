# Changes

## who:  Isaiah Frantz
## when: 08/03/2023
## What:
 - Refactored ugly_lib from a module of functions to a set of classes to make it easier to test
 - Added ability to set necessary args from environment variables in wrapper instead of requiring options to adhere to ci/cd standards better
 - added first set of pytest test for Ugly.ValidateIP()
