# -*- coding: utf-8 -*-

from xmppflask import XmppFlask
app = XmppFlask(__name__)

weather_dict = {
    'Kiev': u"+19 raining. ARGH!!",
    'Amsterdam': u"+23 sunny. ARRRGH!!",
}


def get_weather_for_city(city):
    return (
        weather_dict.get(
            city,
            u"Weather for %(city)s unknown. ARHG!!" % dict(city=city)))


def get_weather_cities():
    return weather_dict.keys()


@app.route('ping')
def ping():
    return 'pong'


@app.route('help')
def help():
    return (u'Type "weather in <city_name>" to get weather in that city.\n'
            u'Type "cities" to get list of cities.')


@app.route('cities')
def cities():
    return u', '.join(get_weather_cities())


@app.route('weather in <city>')
def weather(city):
    return get_weather_for_city(city)
