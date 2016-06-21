import os
import base64
import functools

from sqlalchemy.orm import class_mapper, ColumnProperty
from sqlalchemy.sql.functions import random
from sqlalchemy.exc import OperationalError

from frog import db


class as_dict(object):
    def __init__(self, single=False):
        self.single_item = single

    def __call__(self, func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            result = func(*args, **kwargs)

            # Allow Nones to fall through
            if result is not None:
                if self.single_item:
                    return result._asdict()
                else:
                    as_list = list(result)
                    return [item._asdict() for item in as_list]

        return wrapper


class Tip(db.Model):
    __tablename__ = 'tips'
    number = db.Column('id', db.Integer, primary_key=True)
    tip = db.Column(db.String(255))
    approved = db.Column(db.Boolean())


class Auth(db.Model):
    __tablename__ = 'auth'
    id = db.Column(db.Integer, primary_key=True)
    phrase = db.Column(db.String(255))
    comment = db.Column(db.String(255))
    revoked = db.Column(db.Boolean())


## DEAL WITH THAT TROUBLESOME GENIE.

class PhraseError(Exception):
    pass


def open_sesame(master_phrase, phrase):
    if phrase == master_phrase:
        return True

    try:
        return db.session.query(Auth.phrase, Auth.revoked) \
                         .filter(Auth.revoked == False) \
                         .filter(Auth.phrase == phrase) \
                         .one_or_none() is not None
    except OperationalError:
        return False


def genie_remember_this_phrase(comment):
    try:
        # OH BOY, OUR OWN CRYPTO!!!
        random_bytes = os.urandom(32)
        phrase = base64.b64encode(random_bytes).decode('utf-8')
        auth = Auth(phrase=phrase, revoked=False, comment=comment)
        db.session.add(auth)
        db.session.commit()
        return auth.phrase, auth.id
    except OperationalError:
        raise PhraseError('PHRASE COULD NOT BE REMEMBERED.')


def genie_forget_this_phrase(id):
    try:
        db.session.query(Auth.id).filter(Auth.id == id) \
                                 .update({'revoked': True})
        db.session.commit()
    except OperationalError:
        raise PhraseError('PHRASE COULD NOT BE FORGOTTEN.')


@as_dict()
def genie_share_your_knowledge():
    try:
        return db.session.query(Auth.id, Auth.comment).all()
    except OperationalError:
        raise PhraseError("COULD NOT SHARE THE GENIE'S KNOWLEDGE.")


## A TIP FOR ALL AND FOR ALL A GOOD TIP.

class QueryTipError(Exception):
    pass


class CramTipError(Exception):
    pass


class ApproveTipError(Exception):
    pass


class SearchTipError(Exception):
    pass


class TipMaster(object):

    CROAK_SIZE = 50
    SEARCH_SIZE = 100

    def __init__(self):
        # OH GOD THE GLOBALS ARE LEAKING
        self.session = db.session

    @as_dict()
    def some_tips(self, super_secret_info=False, approved_only=True):
        try:
            return self._tip_query(super_secret_info, approved_only) \
                       .order_by(random()).limit(self.CROAK_SIZE) \
                       .all()
        except OperationalError:
            raise QueryTipError('TIP COULD NOT BE QUERIED.')

    @as_dict(single=True)
    def just_the_tip(self, number, super_secret_info=False, approved_only=True):
        try:
            return self._tip_query(super_secret_info, approved_only) \
                       .filter(Tip.number == number) \
                       .one_or_none()
        except OperationalError:
            raise QueryTipError('TIP COULD NOT BE QUERIED.')

    @as_dict()
    def search_for_spock(self, fat_blob, approved_only, limit=None):
        limit = limit or self.SEARCH_SIZE

        try:
            fat_blob = fat_blob.replace(' ', '%').upper()
            return self._tip_query(super_secret_info=True, approved_only=approved_only) \
                       .filter(Tip.tip.like('%{0}%'.format(fat_blob), escape='\\')) \
                       .limit(limit) \
                       .all()
        except OperationalError:
            raise SearchTipError('YOUR BIG DUMB CRITERIA COULD NOT BE SEARCHED FOR.')

    def cram_tip(self, text):
        session = self.session
        try:
            # SOME VERY IMPORTANT VERIFICATION
            if text.upper() != text:
                raise CramTipError('TIPS MUST BE IN UPPERCASE. HOW DID YOU NOT NOTICE THAT?')

            if not text.endswith('.'):
                raise CramTipError('TIPS MUST END WITH A FULL STOP. THIS THING --> .')

            if 'FROG' not in text:
                raise CramTipError('FROG TIPS MUST CONTAINS AT LEAST ONE MENTION OF THE TITULAR CHARACTER.')

            # YOU MADE IT!!!
            tip = Tip(tip=text, approved=False)
            session.add(tip)
            session.commit()
            return tip.number

        except OperationalError:
            raise CramTipError('COULD NOT ADD TIP.')

    def approve_of_your_child(self, number, approve):
        try:
            tip = db.session.query(Tip).filter(Tip.number == number).one_or_none()

            if tip is None:
                raise ModerateTipError()

            tip.approved = approve
            self.session.commit()
        except OperationalError:
            raise ApproveTipError()

    def _tip_query(self, super_secret_info, approved_only):
        fields = [Tip.number, Tip.tip]

        if super_secret_info:
            fields.append(Tip.approved)

        query = self.session.query(*fields)

        if approved_only:
            query = query.filter(Tip.approved == True)

        return query
