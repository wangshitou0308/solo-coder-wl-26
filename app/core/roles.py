from enum import Enum


class UserRole(str, Enum):
    FAMILY_MEMBER = "family_member"
    DRIVER = "driver"
    HALL_ADMIN = "hall_admin"
    CREMATION_OPERATOR = "cremation_operator"
    FINANCE = "finance"
    DIRECTOR = "director"


ROLE_HIERARCHY = {
    UserRole.DIRECTOR: [
        UserRole.DIRECTOR,
        UserRole.FINANCE,
        UserRole.HALL_ADMIN,
        UserRole.CREMATION_OPERATOR,
        UserRole.DRIVER,
        UserRole.FAMILY_MEMBER,
    ],
    UserRole.FINANCE: [
        UserRole.FINANCE,
        UserRole.FAMILY_MEMBER,
    ],
    UserRole.HALL_ADMIN: [
        UserRole.HALL_ADMIN,
        UserRole.FAMILY_MEMBER,
    ],
    UserRole.CREMATION_OPERATOR: [
        UserRole.CREMATION_OPERATOR,
        UserRole.FAMILY_MEMBER,
    ],
    UserRole.DRIVER: [
        UserRole.DRIVER,
        UserRole.FAMILY_MEMBER,
    ],
    UserRole.FAMILY_MEMBER: [
        UserRole.FAMILY_MEMBER,
    ],
}


def has_permission(user_role: UserRole, required_role: UserRole) -> bool:
    return required_role in ROLE_HIERARCHY.get(user_role, [])


ROLE_NAMES = {
    UserRole.FAMILY_MEMBER: "家属",
    UserRole.DRIVER: "接运司机",
    UserRole.HALL_ADMIN: "告别厅管理员",
    UserRole.CREMATION_OPERATOR: "火化间操作员",
    UserRole.FINANCE: "财务",
    UserRole.DIRECTOR: "馆长",
}
