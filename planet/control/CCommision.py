from planet.common.token_handler import admin_required
from planet.config.enums import UserIdentityStatus
from planet.common.params_validates import parameter_required
from planet.models import User


class CCommision:

    @admin_required
    def list(self):
        data = parameter_required()
        mobile = data.get('mobile')
        agent_query = User.qeury.filter(
            User.isdelete == True,
            User.USlevel == UserIdentityStatus.agent.value
        )
        if mobile:
            mobile = mobile.strip()
            agent_query = agent_query.filter(
                User.UStelphone.contains(mobile)
            )

