from datetime import datetime


class MessageLogger:

    def __init__(self, client):
        self.id = client.id
        self.loop = client.loop
        self.dt = datetime.now()
        self.preface = '[{}][{}][{}]'.format(
            self.dt, self.id, self.__class__.__name__)

    def send(self, ctx):
        print('{} send: id={ctx.id}, channel.id={ctx.channel.id}, content={ctx.content}'.format(
            self.preface, ctx=ctx))

    def edit(self, before, after):
        return None

    def delete(self, ctx):
        print('{} delete: id={ctx.id}, channel.id={ctx.channel.id}, content={ctx.content}'.format(
            self.preface, ctx=ctx))


class Logger:
    def __init__(self, client):
        self.id = client.id
        self.loop = client.loop
        self.dt = datetime.now()
        self.preface = '[{}][{}][{}]'.format(
            self.dt, self.id, self.__class__.__name__)

    def new_user(self, user):
        print('{} new_user: id={user.id}, user={user}'.format(
            self.preface, user=user))
