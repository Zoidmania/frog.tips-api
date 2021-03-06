from flask import abort, request, render_template, Blueprint, Response
import flask.json
from pyasn1.codec.der import encoder

from frog.christmas_tree_monster import TipMaster
from frog.smooshing import FrogTip, Croak
from frog.high_score import BaseApiResponse, ApiError
from frog.plop import GermanTranslator


api = Blueprint('api', __name__, url_prefix='/api/1')
translator = GermanTranslator()
tip_master = TipMaster()


def convert_application_der_stream(data, status, content_type):
    # ASN1 provided for horrible crypto nerds
    try:
        data = Croak.from_tips(iter(data['tips']))
    except (KeyError, TypeError):
        data = FrogTip.from_tip(data)

    return encoder.encode(data)


def api_response(data=None, status=None):
    converters = (
        ('application/der-stream', convert_application_der_stream),
    )
    return BaseApiResponse(data=data, status=status, converters=converters)


@api.route('/tips/<int:num>')
def tip(num):
    """\
    List a single tip duh.
    """
    tip = tip_master.just_the_tip(num)
    if tip is None:
        return api_response(status=404)
    else:
        return api_response(data=tip)


@api.route("/tips", defaults={'lang': 'en'})
@api.route("/tips/", defaults={'lang': 'en'})
@api.route('/tips/<lang>')
def tips(lang):
    """\
    List a whole bunch of tips in whatever big fat dumb format you want.
    """
    tips = tip_master.some_tips()

    if lang == 'de':
        for tip in tips:
            tip['tip'] = translator.translate(tip['tip'])

    return api_response(data={'tips': tips})


@api.route("/")
def root():
    return Response(response=render_template('RFC42069.txt'), mimetype='text/plain')
