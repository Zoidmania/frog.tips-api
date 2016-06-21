from flask import abort, request, render_template, Blueprint, Response
import flask.json
from pyasn1.codec.der import encoder

from frog.christmas_tree_monster import TipMaster
from frog.smooshing import FrogTip, Croak


class ApiResponse(Response):

    der_mimetype = 'application/der-stream'
    default_mimetype = 'application/json'

    def __init__(self, response, **kwargs):
        if self.wants_der():
            response = self._to_der_response(response)
            kwargs['mimetype'] = self.der_mimetype
        else:
            response = self._to_default_response(response)

        super(ApiResponse, self).__init__(response, **kwargs)

    def _to_default_response(self, response):
        if isinstance(response, dict):
            return flask.json.dumps(obj=response)
        else:
            # When in duck typing Rome, quack as the Romans do or bark or woof or whatever (you know those Romans)
            tips = list(response)
            return flask.json.dumps(obj={'tips': tips})

    def _to_der_response(self, response):
        # ASN1 provided for horrible crypto nerds
        try:
            tips = iter(response)
            data = Croak.from_tips(tips)
        except TypeError:
            tip = response
            data = FrogTip.from_tip(tip)

        return encoder.encode(data)

    def wants_der(self):
        # Baby, we all want some DER
        wants = request.accept_mimetypes.best_match([self.default_mimetype, self.der_mimetype])
        return wants == self.der_mimetype


api = Blueprint('api', __name__, url_prefix='/api/1')
tip_master = TipMaster()


@api.route('/tips/<int:num>')
def tip(num):
    """\
    List a single tip duh.
    """
    tip = tip_master.just_the_tip(num)

    if tip is None:
        return abort(404)
    else:
        return ApiResponse(tip)


@api.route("/tips")
@api.route('/tips/')
def tips():
    """\
    List a whole bunch of tips in whatever big fat dumb format you want.
    """
    tips = tip_master.some_tips()
    return ApiResponse(tips)


@api.route("/")
def root():
    return Response(response=render_template('RFC42069.txt'), mimetype='text/plain')
