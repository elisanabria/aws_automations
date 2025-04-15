# Ephemeral Resources Lifecycle

Automation for control of Ephemeral Resources. For EC2 and RDS resources.

Controls the creation date and notifies their expiration according to the criteria defined (default: 30 days).

When any of these resources is created and tagged as "Ephemeral=True", additional tags (CreatedBy and CreationDate) are added. Once the expiration period has passed, a notification is sent to SecurityHub as a failed control, as well as a validation Email is sent, so the Infrastructure-Security Team takes the corresponding action.
