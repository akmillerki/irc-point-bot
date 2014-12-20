import irc.bot

class PointBot(irc.bot.SingleServerIRCBot):

    def __init__(self, channel, prefix='!point', nickname='point_bot', server='irc.freenode.net', port=6667):
        super(PointBot, self).__init__([(server, port)], nickname, nickname)
        self.channel = channel
        self.prefix = prefix

    def on_nicknameinuse(self, connection, event):
        connection.nick(connection.get_nickname() + '_')

    def on_welcome(self, connection, event):
        connection.join(self.channel)

    def on_pubmsg(self, connection, event):
        message = event.arguments[0]
        if message.startswith(self.prefix):
            point_message = message[len(self.prefix):]
            self.process_point_message(point_message, connection, event)

    def process_point_message(self, message, connection, event):
        try:
            value_string, target = message.split()
            value = int(value_string)
            connection.privmsg(self.channel, '{} given to {}'.format(value, target))
        except:
            connection.privmsg(self.channel, 'Error')

def main():
    bot = PointBot('##cm')
    bot.start()

if __name__ == '__main__': main()
