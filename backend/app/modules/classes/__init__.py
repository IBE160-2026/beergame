"""Classes (Epic 4, FR-6–FR-10). A Lecturer creates a Class and owns it (Story 4.1). Other modules
import only `classes.service`. Personal data (Roster addresses, staged uploads) lives in `identity`
tables, which `classes` reaches only through `identity.service` (AD-14); `identity` imports nothing
from here: `classes.service` registers its revoke blocker with `identity` at import."""
