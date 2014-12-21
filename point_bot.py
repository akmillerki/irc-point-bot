import argparse
import collections
import dotenv
import irc.bot
import itertools
import logging
import os
import yaml

logger = logging.getLogger('point_bot')
logger.addHandler(logging.NullHandler())

class PointBot(irc.bot.SingleServerIRCBot):

    HELP_MESSAGE_FORMAT = 'Try {prefix} [(<points> <nick>) | (stats [<nick>]) | (remove <nick>)]'
    STATS_COMMAND = 'stats'
    REMOVE_COMMAND = 'remove'
    TOP_COUNT = 20
    TOP_MESSAGE_FORMAT = 'Top {count}'
    TOP_ENTRY_FORMAT = '{value} - {nick}'
    NO_ENTRIES_MESSAGE = 'No recorded points'
    SELF_REMOVAL_MESSAGES = [
        'You can\'t remove yourself!',
        'Why should I let you do that?',
        'Nice try',
        'I don\'t think I should let you do that',
    ]
    REMOVAL_MESSAGE_FORMAT = '{source} removed record of points for {target}'
    REMOVAL_HELP_MESSAGE_FORMAT = 'Use the form: {prefix} remove <nick>'
    NO_POINTS_RECORDED_MESSAGE_FORMAT = 'No points recorded for {target}!'
    SELF_POINTS_MESSAGES = [
        'You can\'t give yourself points!',
        'That\'s not allowed',
        'Did you think that was going to work?',
        'It\'s better to give than to receive!',
    ]
    POINTS_MESSAGES = [
        (
            '{source} gave {value} point{plural_value} to {target}!',
            '{source} took {value} point{plural_value} from {target}!'
        ),
        (
            '{value} point{plural_value} to {target}!',
            '{value} point{plural_value} from {target}!'
        ),
        (
            '{target} is the proud owner of {value} more point{plural_value}',
            '{target} has {value} fewer point{plural_value} now'
        ),
        (
            '{target} is now {value} point{plural_value} richer!',
            '{target} is now {value} point{plural_value} poorer'
        ),
        (
            '{source} tipped {target} with {value} point{plural_value}!',
            '{source} stripped {target} of {value} precious point{plural_value}'
        ),
    ]
    POINTS_HELP_MESSAGE_FORMAT = 'Use the format: {prefix} <nick> <value>'

    def __init__(self, channel, record_filename, prefix='!points',
            nickname='point_bot', server='irc.freenode.net', port=6667):
        super(PointBot, self).__init__([(server, port)], nickname, nickname)
        logger.debug('Starting')
        self.channel = channel
        self.prefix = prefix
        self.record_filename = record_filename
        self.load_points()
        self.self_removal_messages = itertools.cycle(self.SELF_REMOVAL_MESSAGES)
        self.self_points_messages = itertools.cycle(self.SELF_POINTS_MESSAGES)
        self.points_messages = itertools.cycle(self.POINTS_MESSAGES)

    def load_points(self):
        try:
            with open(self.record_filename, 'r') as record_file:
                self.record = yaml.load(record_file)
                if not self.record:
                    raise ValueError
                logger.info('Points loaded from file')
        except (IOError, ValueError):
            logger.warning('No points loaded from file')
            self.record = {}
        self.record['points'] = self.record.get('points', collections.defaultdict(int))

    def save_points(self):
        with open(self.record_filename, 'w') as record_file:
            yaml.dump(self.record, record_file)
            logger.info('Points saved')

    def on_nicknameinuse(self, connection, event):
        connection.nick(connection.get_nickname() + '_')
        logger.warning('Changing nickname')

    def on_welcome(self, connection, event):
        logger.info('Connected')
        connection.join(self.channel)

    def on_pubmsg(self, connection, event):
        logger.debug('Message received')
        message = event.arguments[0]
        if message.startswith(self.prefix):
            point_message = message[len(self.prefix):].strip()
            if point_message.startswith(self.STATS_COMMAND):
                self.send_point_stats(point_message, connection, event)
            elif point_message.startswith(self.REMOVE_COMMAND):
                self.process_remove_message(point_message, connection, event)
            elif point_message:
                self.process_point_message(point_message, connection, event)
            else:
                self.send_description(connection, event)

    def send_description(self, connection, event):
        logger.debug('Sending description')
        connection.privmsg(self.channel, self.HELP_MESSAGE_FORMAT.format(
                prefix=self.prefix))

    def send_point_stats(self, message, connection, event):
        arguments = message.split()
        try:
            target = arguments[1]
        except IndexError:
            target = None
        top_nicks = sorted(((v,k) for k,v in self.record['points'].iteritems()),
                reverse=True)
        matching_nicks = [(value, nick) for value, nick in top_nicks
                if target is None or nick.startswith(target)]
        if matching_nicks:
            if not target:
                connection.privmsg(self.channel,
                        self.TOP_MESSAGE_FORMAT.format(count=self.TOP_COUNT))
            for value, nick in matching_nicks[:self.TOP_COUNT]:
                connection.privmsg(self.channel,
                        self.TOP_ENTRY_FORMAT.format(value=value, nick=nick))
        else:
            connection.privmsg(self.channel, self.NO_ENTRIES_MESSAGE)
        logger.info('Sent stats')

    def process_remove_message(self, message, connection, event):
        try:
            source = event.source.nick
            target = message.split()[1]
            if source == target:
                connection.privmsg(self.channel, next(self.self_removal_messages))
            else:
                self.remove_points(source, target)
                logger.info('Removed points for {}'.format(target))
                connection.privmsg(self.channel,
                        self.REMOVAL_MESSAGE_FORMAT.format(source=source,
                                                           target=target))
        except IndexError:
            connection.privmsg(self.channel,
                    self.REMOVAL_HELP_MESSAGE_FORMAT.format(prefix=self.prefix))
        except KeyError:
            connection.privmsg(self.channel,
                    self.NO_POINTS_RECORDED_MESSAGE_FORMAT.format(target))

    def process_point_message(self, message, connection, event):
        try:
            source = event.source.nick
            target, value_string = message.split()
            value = int(value_string)
            if source == target:
                connection.privmsg(self.channel, next(self_points_messages))
            else:
                logger.info('Giving points {} -> {}: {}'.format(source, target, value))
                self.give_points(source, value, target)
                plural_value = '' if value == 1 else 's'
                points_message = next(self.points_messages)[0 if value >= 0 else 1]
                connection.privmsg(self.channel,
                        points_message.format(source=source,
                                              value=abs(value),
                                              plural_value=plural_value,
                                              target=target))
        except ValueError:
            connection.privmsg(self.channel,
                    self.POINTS_HELP_MESSAGE_FORMAT.format(prefix=self.prefix))

    def remove_points(self, source, target):
        del self.record['points'][target]
        self.save_points()

    def give_points(self, source, value, target):
        self.record['points'][target] += value
        self.save_points()

def main():
    import logging.config
    with open(os.path.join(os.path.dirname(__file__), 'logging.yml'), 'r') as config:
        logging.config.dictConfig(yaml.load(config))

    dotenv.load_dotenv(os.path.join(os.path.dirname(__file__), '.env'))
    parser = argparse.ArgumentParser(description='IRC Bot for Keeping Score')

    if os.environ.get('CHANNEL'):
        parser.add_argument('--channel', default=os.environ.get('CHANNEL'))
    else:
        parser.add_argument('channel')
    if os.environ.get('RECORD'):
        parser.add_argument('--record', default=os.environ.get('RECORD'))
    else:
        parser.add_argument('record')

    args = parser.parse_args()
    bot = PointBot(args.channel, args.record)
    bot.start()

if __name__ == '__main__': main()
