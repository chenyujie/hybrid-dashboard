from portas.db.models import Environment
from portas.db.session import get_session


class EnvironmentRepository(object):
    def list(self):
        session = get_session()
        return session.query(Environment).all()

    def add(self, values):
        session = get_session()
        with session.begin():
            env = Environment()
            env.update(values)
            session.add(env)
            return env

    # def update(self, env):