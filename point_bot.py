import collections
import irc.bot
import yaml

yaml.add_representer(collections.defaultdict, yaml.representer.Representer.represent_dict)

class PointBot(irc.bot.SingleServerIRCBot):

    def __init__(self, channel, record_filename, prefix='!points', nickname='point_bot', server='irc.freenode.net', port=6667):
        super(PointBot, self).__init__([(server, port)], nickname, nickname)
        self.channel = channel
        self.prefix = prefix
        self.record_filename = record_filename
        self.load_points()

    def load_points(self):
        try:
            with open(self.record_filename, 'r') as record_file:
                self.record = yaml.load(record_file)
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
            point_message = message[len(self.prefix):].strip()
            if point_message.startswith('stats'):
                self.send_point_stats(point_message, connection, event)
            elif point_message.startswith('remove'):
                self.process_remove_message(point_message, connection, event)
            elif point_message:
                self.process_point_message(point_message, connection, event)
            else:
                self.send_description(connection, event)

    def send_description(self, connection, event):
        connection.privmsg(self.channel, 'Try {} [(<points> <nick>) | (stats [<nick>]) | (remove <nick>)]'.format(self.prefix))

    def send_point_stats(self, message, connection, event):
        arguments = message.split()
        try:
            target = arguments[1]
        except IndexError:
            target = None
        count_to_show = 20
        if not target:
            connection.privmsg(self.channel, 'Top {}'.format(count_to_show))
        top_nicks = sorted(((v,k) for k,v in self.record['points'].iteritems()), reverse=True)
        matching_nicks = [(value, nick) for value, nick in top_nicks
                if target is None or nick.startswith(target)]
        for value, nick in matching_nicks[:count_to_show]:
            connection.privmsg(self.channel, '{} - {}'.format(value, nick))

    def process_remove_message(self, message, connection, event):
        try:
            source = event.source.nick
            target = message.split()[1]
            if source == target:
                connection.privmsg(self.channel, 'You can\'t remove yourself!')
            else:
                self.remove_points(source, target)
                connection.privmsg(self.channel, '{} removed record of points for {}'.format(source, target))
        except IndexError:
            connection.privmsg(self.channel, 'Use the form: {} remove <nick>'.format(self.prefix))
        except KeyError:
            connection.privmsg(self.channel, 'No points recorded for {}!'.format(target))

    def process_point_message(self, message, connection, event):
        try:
            source = event.source.nick
            target, value_string = message.split()
            value = int(value_string)
            if source == target:
                connection.privmsg(self.channel, 'You can\'t give yourself points!')
            else:
                self.give_points(source, value, target)
                connection.privmsg(self.channel, '{} gave {} to {}'.format(source, value, target))
        except ValueError:
            connection.privmsg(self.channel, 'Use the format: {} <nick> <value>'.format(self.prefix))

    def remove_points(self, source, target):
        del self.record['points'][target]
        self.save_points()

    def give_points(self, source, value, target):
        self.record['points'][target] += value
        self.save_points()

def main():
    bot = PointBot('##cm', 'record.yml')
    bot.start()

if __name__ == '__main__': main()
