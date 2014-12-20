import collections
import irc.bot
import yaml

yaml.add_representer(collections.defaultdict, yaml.representer.Representer.represent_dict)

class PointBot(irc.bot.SingleServerIRCBot):

    def __init__(self, channel, record_filename, prefix='!point', nickname='point_bot', server='irc.freenode.net', port=6667):
        super(PointBot, self).__init__([(server, port)], nickname, nickname)
        self.channel = channel
        self.prefix = prefix
        self.record_filename = record_filename
        self.load_points()

    def load_points(self):
        try:
            with open(self.record_filename, 'r') as record_file:
                self.record = yaml.safe_load(record_file)
                if not self.record:
                    raise ValueError
        except (IOError, ValueError):
            self.record = {}
        self.record['points'] = self.record.get('points', collections.defaultdict(int))

    def save_points(self):
        with open(self.record_filename, 'w') as record_file:
            yaml.dump(self.record, record_file)

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
            source = event.source.nick
            value_string, target = message.split()
            value = int(value_string)
            self.give_points(source, value, target)
            connection.privmsg(self.channel, '{} gave {} to {}'.format(source, value, target))
        except ValueError:
            connection.privmsg(self.channel, 'Use the format: {} <value> <nick>'.format(self.prefix))

    def give_points(self, source, value, target):
        self.record['points'][target] += value
        self.save_points()

def main():
    bot = PointBot('##cm', 'record.yml')
    bot.start()

if __name__ == '__main__': main()
