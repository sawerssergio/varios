# -*- coding: utf-8 -*-			
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2010 Tiny SPRL (<http://tiny.be>).
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

import logging
import time

from openerp import tools, osv
from openerp import models, fields, api, _
from openerp.tools import float_is_zero
from openerp.tools.translate import _

import openerp.addons.decimal_precision as dp
import openerp.addons.product.product
from codigoControl.CodigoControl import CodigoControl
from num2words import num2words
from PIL import Image
from datetime import datetime
from codigoControl.CodigoControl import CodigoControl as cc

try:
    import cStringIO as StringIO
except ImportError:
    import StringIO

_logger = logging.getLogger(__name__)

# ----------------------------------------
# Crop Image
# ----------------------------------------
def crop_image(data, type='top', ratio=False, thumbnail_ratio=None, image_format="PNG"):
    """ Used for cropping image and create thumbnail
        :param data: base64 data of image.
        :param type: Used for cropping position possible
            Possible Values : 'top', 'center', 'bottom'
        :param ratio: Cropping ratio
            e.g for (4,3), (16,9), (16,10) etc
            send ratio(1,1) to generate square image
        :param thumbnail_ratio: It is size reduce ratio for thumbnail
            e.g. thumbnail_ratio=2 will reduce your 500x500 image converted in to 250x250
        :param image_format: return image format PNG,JPEG etc
    """
    if not data:
        return False
    image_stream = Image.open(StringIO.StringIO(data.decode('base64')))
    output_stream = StringIO.StringIO()
    w, h = image_stream.size
    new_h = h
    new_w = w

    if ratio:
        w_ratio, h_ratio = ratio
        new_h = (w * h_ratio) / w_ratio
        new_w = w
        if new_h > h:
            new_h = h
            new_w = (h * w_ratio) / h_ratio

    if type == "top":
        cropped_image = image_stream.crop((0, 0, new_w, new_h))
        cropped_image.save(output_stream, format=image_format)
    elif type == "center":
        cropped_image = image_stream.crop(((w - new_w) / 2, (h - new_h) / 2, (w + new_w) / 2, (h + new_h) / 2))
        cropped_image.save(output_stream, format=image_format)
    elif type == "bottom":
        cropped_image = image_stream.crop((0, h - new_h, new_w, h))
        cropped_image.save(output_stream, format=image_format)
    else:
        raise ValueError('ERROR: invalid value for crop_type')
    # TDE FIXME: should not have a ratio, makes no sense -> should have maximum width (std: 64; 256 px)
    if thumbnail_ratio:
        thumb_image = Image.open(StringIO.StringIO(output_stream.getvalue()))
        thumb_image.thumbnail((new_w / thumbnail_ratio, new_h / thumbnail_ratio), Image.ANTIALIAS)
        thumb_image.save(output_stream, image_format)
    return output_stream.getvalue().encode('base64')

class pos_config(models.Model):
    _name = 'pos.config'

    POS_CONFIG_STATE = [
        ('active', 'Active'),
        ('inactive', 'Inactive'),
        ('deprecated', 'Deprecated')
    ]

    @api.v7
    def _get_currency(self, cr, uid, ids, context=None):
        result = dict.fromkeys(ids, False)
        for pos_config in self.browse(cr, uid, ids, context=context):
            if pos_config.journal_id:
                currency_id = pos_config.journal_id.currency.id or pos_config.journal_id.company_id.currency_id.id
            else:
                currency_id = self.pool['res.users'].browse(cr, uid, uid, context=context).company_id.currency_id.id
            result[pos_config.id] = currency_id
        return result

    @api.v8
    @api.one
    @api.depends('journal_id')
    def _get_currency(self):
        if self.journal_id:
            self.currency_id = self.journal_id.currency.id or self.journal_id.company_id.currency_id.id
        else:
            self.currency_id = self.env.user.company_id.currency_id.id

    name                   = fields.Char('Point of Sale Name', select=1, required=True,
           help="An internal identification of the point of sale")
    journal_ids            = fields.Many2many('account.journal', 'pos_config_journal_rel',
             'pos_config_id', 'journal_id', 'Available Payment Methods',
             domain="[('journal_user', '=', True ), ('type', 'in', ['bank', 'cash'])]",)
    picking_type_id        = fields.Many2one('stock.picking.type', 'Picking Type')
    stock_location_id      = fields.Many2one('stock.location', 'Stock Location', domain=[('usage', '=', 'internal')], required=True)
    journal_id             = fields.Many2one('account.journal', 'Sale Journal',
             domain=[('type', '=', 'sale')],
             help="Accounting journal used to post sales entries.")
    currency_id            = fields.Many2one(compute="_get_currency", comodel_name="res.currency")
    iface_self_checkout    = fields.Boolean('Self Checkout Mode', # FIXME = this field is obsolete
             help="Check this if this point of sale should open by default in a self checkout mode. If unchecked, SawersSystem uses the normal cashier mode by default.")
    iface_cashdrawer       = fields.Boolean('Cashdrawer', help="Automatically open the cashdrawer")
    iface_payment_terminal = fields.Boolean('Payment Terminal', help="Enables Payment Terminal integration")
    iface_electronic_scale = fields.Boolean('Electronic Scale', help="Enables Electronic Scale integration")
    iface_vkeyboard        = fields.Boolean('Virtual KeyBoard', help="Enables an integrated Virtual Keyboard")
    iface_print_via_proxy  = fields.Boolean('Print via Proxy', help="Bypass browser printing and prints via the hardware proxy")
    iface_scan_via_proxy   = fields.Boolean('Scan via Proxy', help="Enable barcode scanning with a remotely connected barcode scanner")
    iface_invoicing        = fields.Boolean('Invoicing',help='Enables invoice generation from the Point of Sale')
    iface_big_scrollbars   = fields.Boolean('Large Scrollbars',help='For imprecise industrial touchscreens')
    receipt_header   = fields.Text('Receipt Header',help="A short text that will be inserted as a header in the printed receipt")
    receipt_footer   = fields.Text('Receipt Footer',help="A short text that will be inserted as a footer in the printed receipt")
    proxy_ip         =       fields.Char('IP Address', help='The hostname or ip address of the hardware proxy, Will be autodetected if left empty', size=45)

    state            = fields.Selection(POS_CONFIG_STATE, 'Status', required=True, readonly=True, copy=False)
    sequence_id      = fields.Many2one('ir.sequence', 'Order IDs Sequence', readonly=True,
            help="This sequence is automatically created by SawersSystem but you can change it "\
                "to customize the reference numbers of your orders.", copy=False)
    session_ids      = fields.One2many('pos.session', 'config_id', 'Sessions')
    group_by         = fields.Boolean('Group Journal Items', help="Check this if you want to group the Journal Items by Product while closing a Session")
    pricelist_id     = fields.Many2one('product.pricelist','Pricelist', required=True)
    company_id       = fields.Many2one('res.company', 'Company', required=True)
    barcode_product  = fields.Char('Product Barcodes', size=64, help='The pattern that identifies product barcodes')
    barcode_cashier  = fields.Char('Cashier Barcodes', size=64, help='The pattern that identifies cashier login barcodes')
    barcode_customer = fields.Char('Customer Barcodes',size=64, help='The pattern that identifies customer\'s client card barcodes')
    barcode_price    = fields.Char('Price Barcodes',   size=64, help='The pattern that identifies a product with a barcode encoded price')
    barcode_weight   = fields.Char('Weight Barcodes',  size=64, help='The pattern that identifies a product with a barcode encoded weight')
    barcode_discount = fields.Char('Discount Barcodes',  size=64, help='The pattern that identifies a product with a barcode encoded discount')
    authorization    = fields.Char('authorization', size=64, help='authorization')
    key              = fields.Char('key',size=64, help='key')
    limit_date       = fields.Date('Limit Date')
    usd_rate         = fields.Float(help='USD RATE',string='USD Rate')

    def _check_cash_control(self, cr, uid, ids, context=None):
        return all(
            (sum(int(journal.cash_control) for journal in record.journal_ids) <= 1)
            for record in self.browse(cr, uid, ids, context=context)
        )

    def _check_company_location(self, cr, uid, ids, context=None):
        for config in self.browse(cr, uid, ids, context=context):
            if config.stock_location_id.company_id and config.stock_location_id.company_id.id != config.company_id.id:
                return False
        return True

    def _check_company_journal(self, cr, uid, ids, context=None):
        for config in self.browse(cr, uid, ids, context=context):
            if config.journal_id and config.journal_id.company_id.id != config.company_id.id:
                return False
        return True

    def _check_company_payment(self, cr, uid, ids, context=None):
        for config in self.browse(cr, uid, ids, context=context):
            journal_ids = [j.id for j in config.journal_ids]
            if self.pool['account.journal'].search(cr, uid, [
                    ('id', 'in', journal_ids),
                    ('company_id', '!=', config.company_id.id)
                ], count=True, context=context):
                return False
        return True

    _constraints = [
        (_check_cash_control, "You cannot have two cash controls in one Point Of Sale !", ['journal_ids']),
        (_check_company_location, "The company of the stock location is different than the one of point of sale", ['company_id', 'stock_location_id']),
        (_check_company_journal, "The company of the sale journal is different than the one of point of sale", ['company_id', 'journal_id']),
        (_check_company_payment, "The company of a payment method is different than the one of point of sale", ['company_id', 'journal_ids']),
    ]

    def name_get(self, cr, uid, ids, context=None):
        result = []
        states = {
            'opening_control': _('Opening Control'),
            'opened': _('In Progress'),
            'closing_control': _('Closing Control'),
            'closed': _('Closed & Posted'),
        }
        for record in self.browse(cr, uid, ids, context=context):
            if (not record.session_ids) or (record.session_ids[0].state=='closed'):
                result.append((record.id, record.name+' ('+_('not used')+')'))
                continue
            session = record.session_ids[0]
            result.append((record.id, record.name + ' ('+session.user_id.name+')')) #, '+states[session.state]+')'))
        return result

    def _default_sale_journal(self, cr, uid, context=None):
        company_id = self.pool.get('res.users').browse(cr, uid, uid, context=context).company_id.id
        res = self.pool.get('account.journal').search(cr, uid, [('type', '=', 'sale'), ('company_id', '=', company_id)], limit=1, context=context)
        return res and res[0] or False

    def _default_pricelist(self, cr, uid, context=None):
        res = self.pool.get('product.pricelist').search(cr, uid, [('type', '=', 'sale')], limit=1, context=context)
        return res and res[0] or False

    def _get_default_location(self, cr, uid, context=None):
        wh_obj = self.pool.get('stock.warehouse')
        user = self.pool.get('res.users').browse(cr, uid, uid, context)
        res = wh_obj.search(cr, uid, [('company_id', '=', user.company_id.id)], limit=1, context=context)
        if res and res[0]:
            return wh_obj.browse(cr, uid, res[0], context=context).lot_stock_id.id
        return False

    def _get_default_company(self, cr, uid, context=None):
        company_id = self.pool.get('res.users')._get_company(cr, uid, context=context)
        return company_id

    _defaults = {
        'state' : POS_CONFIG_STATE[0][0],
        'journal_id': _default_sale_journal,
        'group_by' : True,
        'pricelist_id': _default_pricelist,
        'iface_invoicing': True,
        'stock_location_id': _get_default_location,
        'company_id': _get_default_company,
        'barcode_product': '*', 
        'barcode_cashier': '041*', 
        'barcode_customer':'042*', 
        'barcode_weight':  '21xxxxxNNDDD', 
        'barcode_discount':'22xxxxxxxxNN', 
        'barcode_price':   '23xxxxxNNNDD', 
    }

    def onchange_picking_type_id(self, cr, uid, ids, picking_type_id, context=None):
        p_type_obj = self.pool.get("stock.picking.type")
        p_type = p_type_obj.browse(cr, uid, picking_type_id, context=context)
        if p_type.default_location_src_id and p_type.default_location_src_id.usage == 'internal' and p_type.default_location_dest_id and p_type.default_location_dest_id.usage == 'customer':
            return {'value': {'stock_location_id': p_type.default_location_src_id.id}}
        return False

    def set_active(self, cr, uid, ids, context=None):
        return self.write(cr, uid, ids, {'state' : 'active'}, context=context)

    def set_inactive(self, cr, uid, ids, context=None):
        return self.write(cr, uid, ids, {'state' : 'inactive'}, context=context)

    def set_deprecate(self, cr, uid, ids, context=None):
        return self.write(cr, uid, ids, {'state' : 'deprecated'}, context=context)

    def create(self, cr, uid, values, context=None):
        ir_sequence = self.pool.get('ir.sequence')
        # force sequence_id field to new pos.order sequence
        values['sequence_id'] = ir_sequence.create(cr, uid, {
            'name': 'POS Order %s' % values['name'],
            'padding': 4,
            'prefix': "%s/"  % values['name'],
            'code': "pos.order",
            'company_id': values.get('company_id', False),
        }, context=context)

        # TODO master: add field sequence_line_id on model
        # this make sure we always have one available per company
        ir_sequence.create(cr, uid, {
            'name': 'POS order line %s' % values['name'],
            'padding': 4,
            'prefix': "%s/"  % values['name'],
            'code': "pos.order.line",
            'company_id': values.get('company_id', False),
        }, context=context)

        return super(pos_config, self).create(cr, uid, values, context=context)

    def unlink(self, cr, uid, ids, context=None):
        for obj in self.browse(cr, uid, ids, context=context):
            if obj.sequence_id:
                obj.sequence_id.unlink()
        return super(pos_config, self).unlink(cr, uid, ids, context=context)

class pos_session(models.Model):
    _name = 'pos.session'
    _order = 'id desc'

    POS_SESSION_STATE = [
        ('opening_control', 'Opening Control'),  # Signal open
        ('opened', 'In Progress'),                    # Signal closing
        ('closing_control', 'Closing Control'),  # Signal close
        ('closed', 'Closed & Posted'),
    ]
    
    @api.v7
    def _compute_cash_all(self, cr, uid, ids, context=None):
        result = dict()

        for record in self.browse(cr, uid, ids, context=context):
            result[record.id] = {
                'cash_journal_id' : False,
                'cash_register_id' : False,
                'cash_control' : False,
            }
            for st in record.statement_ids:
                if st.journal_id.cash_control == True:
                    result[record.id]['cash_control'] = True
                    result[record.id]['cash_journal_id'] = st.journal_id.id
                    result[record.id]['cash_register_id'] = st.id

        return result

    @api.v8
    @api.one
    @api.depends('statement_ids')
    def _compute_cash_all(self):
        self.cash_journal_id = False
        self.cash_register_id = False
        self.cash_control = False
        for st in self.statement_ids:
            if st.journal_id.cash_control == True:
                self.cash_control = True
                self.cash_journal_id = st.journal_id.id
                self.cash_register_id = st.id

    config_id = fields.Many2one(comodel_name='pos.config', string='Point of Sale',
                              help="The physical point of sale you will use.",
                              required=True,
                              select=1,
                              domain="[('state', '=', 'active')]",
                     )

    name = fields.Char('Session ID', required=True, readonly=True)
    user_id = fields.Many2one(comodel_name='res.users', string='Responsible',
                                required=True,
                                select=1,
                                readonly=True,
                                states={'opening_control' : [('readonly', False)]}
                       )
    currency_id = fields.Many2one(string="Currency", related='config_id.currency_id')
    start_at = fields.Datetime('Opening Date', readonly=True)
    stop_at = fields.Datetime('Closing Date', readonly=True)

    state = fields.Selection(POS_SESSION_STATE, 'Status',
                required=True, readonly=True,
                select=1, copy=False)

    sequence_number = fields.Integer('Order Sequence Number', help='A sequence number that is incremented with each order')
    login_number = fields.Integer('Login Sequence Number', help='A sequence number that is incremented each time a user resumes the pos session')

    cash_control = fields.Boolean(compute='_compute_cash_all',
                                     multi='cash',
                                     string='Has Cash Control')
    cash_journal_id = fields.Many2one(compute='_compute_cash_all',
                                        multi='cash', comodel_name='account.journal',
                                        string='Cash Journal', store=True)
    cash_register_id = fields.Many2one(compute='_compute_cash_all',
                                         multi='cash', comodel_name='account.bank.statement',
                                         string='Cash Register', store=True)

    #type='one2many', related='account.cashbox.line',
    opening_details_ids = fields.One2many(related = 'cash_register_id.opening_details_ids', comodel_name='account.cashbox.line',
                string='Opening Cash Control')

    #type='one2many', related='account.cashbox.line', 
    details_ids = fields.One2many(related='cash_register_id.details_ids', string='Cash Control', comodel_name='account.cashbox.line')

    cash_register_balance_end_real = fields.Float(related='cash_register_id.balance_end_real',
                digits_compute=dp.get_precision('Account'),
                string="Ending Balance",
                help="Total of closing cash control lines.",
                readonly=True)

    cash_register_balance_start = fields.Float(related='cash_register_id.balance_start',
                digits_compute=dp.get_precision('Account'),
                string="Starting Balance",
                help="Total of opening cash control lines.",
                readonly=True)

    cash_register_total_entry_encoding = fields.Float(related='cash_register_id.total_entry_encoding',
                string='Total Cash Transaction',
                readonly=True,
                help="Total of all paid sale orders")

    cash_register_balance_end = fields.Float(related='cash_register_id.balance_end',
                type='float',
                digits_compute=dp.get_precision('Account'),
                string="Theoretical Closing Balance",
                help="Sum of opening balance and transactions.",
                readonly=True)

    cash_register_difference = fields.Float(related='cash_register_id.difference',
                type='float',
                string='Difference',
                help="Difference between the theoretical closing balance and the real closing balance.",
                readonly=True)

    journal_ids = fields.Many2many(related='config_id.journal_ids',
                                       readonly=True, comodel_name='account.journal',
                                       string='Available Payment Methods')
    order_ids = fields.One2many('pos.order', 'session_id', 'Orders')

    statement_ids = fields.One2many('account.bank.statement', 'pos_session_id', 'Bank Statement', readonly=True)

    _defaults = {
        'name' : '/',
        'user_id' : lambda obj, cr, uid, context: uid,
        'state' : 'opening_control',
        'sequence_number': 1,
        'login_number': 0,
    }

    _sql_constraints = [
        ('uniq_name', 'unique(name)', "The name of this POS Session must be unique !"),
    ]

    def _check_unicity(self, cr, uid, ids, context=None):
        for session in self.browse(cr, uid, ids, context=None):
            # open if there is no session in 'opening_control', 'opened', 'closing_control' for one user
            domain = [
                ('state', 'not in', ('closed','closing_control')),
                ('user_id', '=', session.user_id.id)
            ]
            count = self.search_count(cr, uid, domain, context=context)
            if count>1:
                return False
        return True

    def _check_pos_config(self, cr, uid, ids, context=None):
        for session in self.browse(cr, uid, ids, context=None):
            domain = [
                ('state', '!=', 'closed'),
                ('config_id', '=', session.config_id.id)
            ]
            count = self.search_count(cr, uid, domain, context=context)
            if count>1:
                return False
        return True

    _constraints = [
        (_check_unicity, "You cannot create two active sessions with the same responsible!", ['user_id', 'state']),
        (_check_pos_config, "You cannot create two active sessions related to the same point of sale!", ['config_id']),
    ]

    def create(self, cr, uid, values, context=None):
        context = dict(context or {})
        config_id = values.get('config_id', False) or context.get('default_config_id', False)
        if not config_id:
            raise osv.except_osv( _('Error!'),
                _("You should assign a Point of Sale to your session."))

        # journal_id is not required on the pos_config because it does not
        # exists at the installation. If nothing is configured at the
        # installation we do the minimal configuration. Impossible to do in
        # the .xml files as the CoA is not yet installed.
        jobj = self.pool.get('pos.config')
        pos_config = jobj.browse(cr, uid, config_id, context=context)
        context.update({'company_id': pos_config.company_id.id})
        if not pos_config.journal_id:
            jid = jobj.default_get(cr, uid, ['journal_id'], context=context)['journal_id']
            if jid:
                jobj.write(cr, openerp.SUPERUSER_ID, [pos_config.id], {'journal_id': jid}, context=context)
            else:
                raise osv.except_osv( _('error!'),
                    _("Unable to open the session. You have to assign a sale journal to your point of sale."))

        # define some cash journal if no payment method exists
        if not pos_config.journal_ids:
            journal_proxy = self.pool.get('account.journal')
            cashids = journal_proxy.search(cr, uid, [('journal_user', '=', True), ('type','=','cash')], context=context)
            if not cashids:
                cashids = journal_proxy.search(cr, uid, [('type', '=', 'cash')], context=context)
                if not cashids:
                    cashids = journal_proxy.search(cr, uid, [('journal_user','=',True)], context=context)

            journal_proxy.write(cr, openerp.SUPERUSER_ID, cashids, {'journal_user': True})
            jobj.write(cr, openerp.SUPERUSER_ID, [pos_config.id], {'journal_ids': [(6,0, cashids)]})


        pos_config = jobj.browse(cr, uid, config_id, context=context)
        bank_statement_ids = []
        for journal in pos_config.journal_ids:
            bank_values = {
                'journal_id' : journal.id,
                'user_id' : uid,
                'company_id' : pos_config.company_id.id
            }
            statement_id = self.pool.get('account.bank.statement').create(cr, uid, bank_values, context=context)
            bank_statement_ids.append(statement_id)

        values.update({
            'name': self.pool['ir.sequence'].get(cr, uid, 'pos.session'),
            'statement_ids' : [(6, 0, bank_statement_ids)],
            'config_id': config_id
        })

        return super(pos_session, self).create(cr, uid, values, context=context)

    def unlink(self, cr, uid, ids, context=None):
        for obj in self.browse(cr, uid, ids, context=context):
            for statement in obj.statement_ids:
                statement.unlink(context=context)
        return super(pos_session, self).unlink(cr, uid, ids, context=context)

    def open_cb(self, cr, uid, ids, context=None):
        """
        call the Point Of Sale interface and set the pos.session to 'opened' (in progress)
        """
        if context is None:
            context = dict()

        if isinstance(ids, (int, long)):
            ids = [ids]

        this_record = self.browse(cr, uid, ids[0], context=context)
        this_record.signal_workflow('open')

        context.update(active_id=this_record.id)

        return {
            'type' : 'ir.actions.act_url',
            'url'  : '/pos/web/',
            'target': 'self',
        }

    def login(self, cr, uid, ids, context=None):
        this_record = self.browse(cr, uid, ids[0], context=context)
        this_record.write({
            'login_number': this_record.login_number+1,
        })

    def wkf_action_open(self, cr, uid, ids, context=None):
        # second browse because we need to refetch the data from the DB for cash_register_id
        for record in self.browse(cr, uid, ids, context=context):
            values = {}
            if not record.start_at:
                values['start_at'] = time.strftime('%Y-%m-%d %H:%M:%S')
            values['state'] = 'opened'
            record.write(values)
            for st in record.statement_ids:
                st.button_open()

        return self.open_frontend_cb(cr, uid, ids, context=context)

    def wkf_action_opening_control(self, cr, uid, ids, context=None):
        return self.write(cr, uid, ids, {'state' : 'opening_control'}, context=context)

    def wkf_action_closing_control(self, cr, uid, ids, context=None):
        for session in self.browse(cr, uid, ids, context=context):
            for statement in session.statement_ids:
                if (statement != session.cash_register_id) and (statement.balance_end != statement.balance_end_real):
                    self.pool.get('account.bank.statement').write(cr, uid, [statement.id], {'balance_end_real': statement.balance_end})
        return self.write(cr, uid, ids, {'state' : 'closing_control', 'stop_at' : time.strftime('%Y-%m-%d %H:%M:%S')}, context=context)

    def wkf_action_close(self, cr, uid, ids, context=None):
        # Close CashBox
        for record in self.browse(cr, uid, ids, context=context):
            for st in record.statement_ids:
                if abs(st.difference) > st.journal_id.amount_authorized_diff:
                    # The pos manager can close statements with maximums.
                    if not self.pool.get('ir.model.access').check_groups(cr, uid, "pos_kingdom.group_pos_manager"):
                        raise osv.except_osv( _('Error!'),
                            _("Your ending balance is too different from the theoretical cash closing (%.2f), the maximum allowed is: %.2f. You can contact your manager to force it.") % (st.difference, st.journal_id.amount_authorized_diff))
                if (st.journal_id.type not in ['bank', 'cash']):
                    raise osv.except_osv(_('Error!'), 
                        _("The type of the journal for your payment method should be bank or cash "))
                getattr(st, 'button_confirm_%s' % st.journal_id.type)(context=context)
        self._confirm_orders(cr, uid, ids, context=context)
        self.write(cr, uid, ids, {'state' : 'closed'}, context=context)

        obj = self.pool.get('ir.model.data').get_object_reference(cr, uid, 'pos_kingdom', 'menu_point_root')[1]
        return {
            'type' : 'ir.actions.client',
            'name' : 'Point of Sale Menu',
            'tag' : 'reload',
            'params' : {'menu_id': obj},
        }

    def _confirm_orders(self, cr, uid, ids, context=None):
        account_move_obj = self.pool.get('account.move')
        pos_order_obj = self.pool.get('pos.order')
        for session in self.browse(cr, uid, ids, context=context):
            local_context = dict(context or {}, force_company=session.config_id.journal_id.company_id.id)
            order_ids = [order.id for order in session.order_ids if order.state == 'paid']

            move_id = account_move_obj.create(cr, uid, {'ref' : session.name, 'journal_id' : session.config_id.journal_id.id, }, context=local_context)

            pos_order_obj._create_account_move_line(cr, uid, order_ids, session, move_id, context=local_context)

            for order in session.order_ids:
                if order.state == 'done':
                    continue
                if order.state not in ('paid', 'invoiced'):
                    raise osv.except_osv(
                        _('Error!'),
                        _("You cannot confirm all orders of this session, because they have not the 'paid' status"))
                else:
                    pos_order_obj.signal_workflow(cr, uid, [order.id], 'done')

        return True

    def open_frontend_cb(self, cr, uid, ids, context=None):
        if not context:
            context = {}
        if not ids:
            return {}
        for session in self.browse(cr, uid, ids, context=context):
            if session.user_id.id != uid:
                raise osv.except_osv(
                        _('Error!'),
                        _("You cannot use the session of another users. This session is owned by %s. Please first close this one to use this point of sale." % session.user_id.name))
        context.update({'active_id': ids[0]})
        return {
            'type' : 'ir.actions.act_url',
            'target': 'self',
            'url':   '/pos/web/',
        }

class pos_order(models.Model):
    _name = "pos.order"
    _description = "Point of Sale"
    _order = "id desc"

    def _order_fields(self, cr, uid, ui_order, context=None):
        return {
            'name':         ui_order['name'],
            'user_id':      ui_order['user_id'] or False,
            'session_id':   ui_order['pos_session_id'],
            'lines':        ui_order['lines'],
            'pos_reference':ui_order['name'],
            'partner_id':   ui_order['partner_id'] or False,
            'type_of':      ui_order['type_of'] or False,
        }

    def _payment_fields(self, cr, uid, ui_paymentline, context=None):
        return {
            'amount':       ui_paymentline['amount'] or 0.0,
            'payment_date': ui_paymentline['name'],
            'statement_id': ui_paymentline['statement_id'],
            'payment_name': ui_paymentline.get('note',False),
            'journal':      ui_paymentline['journal_id'],
        }

    def _process_order(self, cr, uid, order, context=None):
        order_id = self.create(cr, uid, self._order_fields(cr, uid, order, context=context),context)

        for payments in order['statement_ids']:
            self.add_payment(cr, uid, order_id, self._payment_fields(cr, uid, payments[2], context=context), context=context)

        session = self.pool.get('pos.session').browse(cr, uid, order['pos_session_id'], context=context)
        if session.sequence_number <= order['sequence_number']:
            session.write({'sequence_number': order['sequence_number'] + 1})
            session.refresh()

        if not float_is_zero(order['amount_return'], self.pool.get('decimal.precision').precision_get(cr, uid, 'Account')):
            cash_journal = session.cash_journal_id
            if not cash_journal:
                cash_journal_ids = filter(lambda st: st.journal_id.type=='cash', session.statement_ids)
                if not len(cash_journal_ids):
                    raise osv.except_osv( _('error!'),
                        _("No cash statement found for this session. Unable to record returned cash."))
                cash_journal = cash_journal_ids[0].journal_id
            self.add_payment(cr, uid, order_id, {
                'amount': -order['amount_return'],
                'payment_date': time.strftime('%Y-%m-%d %H:%M:%S'),
                'payment_name': _('return'),
                'journal': cash_journal.id,
            }, context=context)
        return order_id

    def create_from_ui(self, cr, uid, orders, context=None):
        # Keep only new orders
        submitted_references = [o['data']['name'] for o in orders]
        existing_order_ids = self.search(cr, uid, [('pos_reference', 'in', submitted_references)], context=context)
        existing_orders = self.read(cr, uid, existing_order_ids, ['pos_reference'], context=context)
        existing_references = set([o['pos_reference'] for o in existing_orders])
        orders_to_save = [o for o in orders if o['data']['name'] not in existing_references]

        order_ids = []

        for tmp_order in orders_to_save:
            to_invoice = tmp_order['to_invoice']
            order = tmp_order['data']
            order_id = self._process_order(cr, uid, order, context=context)
            order_ids.append(order_id)

            try:
                self.signal_workflow(cr, uid, [order_id], 'paid')
            except Exception as e:
                _logger.error('Could not fully process the POS Order: %s', tools.ustr(e))

            if to_invoice:
                self.action_invoice(cr, uid, [order_id], context)
                order_obj = self.browse(cr, uid, order_id, context)
                self.pool['account.invoice'].signal_workflow(cr, uid, [order_obj.invoice_id.id], 'invoice_open')

        return order_ids

    def write(self, cr, uid, ids, vals, context=None):
        res = super(pos_order, self).write(cr, uid, ids, vals, context=context)
        #If you change the partner of the PoS order, change also the partner of the associated bank statement lines
        partner_obj = self.pool.get('res.partner')
        bsl_obj = self.pool.get("account.bank.statement.line")
        if 'partner_id' in vals:
            for posorder in self.browse(cr, uid, ids, context=context):
                if posorder.invoice_id:
                    raise osv.except_osv( _('Error!'), _("You cannot change the partner of a POS order for which an invoice has already been issued."))
                if vals['partner_id']:
                    p_id = partner_obj.browse(cr, uid, vals['partner_id'], context=context)
                    part_id = partner_obj._find_accounting_partner(p_id).id
                else:
                    part_id = False
                bsl_ids = [x.id for x in posorder.statement_ids]
                bsl_obj.write(cr, uid, bsl_ids, {'partner_id': part_id}, context=context)
        return res

    def unlink(self, cr, uid, ids, context=None):
        for rec in self.browse(cr, uid, ids, context=context):
            if rec.state not in ('draft','cancel'):
                raise osv.except_osv(_('Unable to Delete!'), _('In order to delete a sale, it must be new or cancelled.'))
        return super(pos_order, self).unlink(cr, uid, ids, context=context)

    def onchange_partner_id(self, cr, uid, ids, part=False, context=None):
        if not part:
            return {'value': {}}
        pricelist = self.pool.get('res.partner').browse(cr, uid, part, context=context).property_product_pricelist.id
        return {'value': {'pricelist_id': pricelist}}

    @api.one
    @api.depends('statement_ids','lines')
    def _amount_all(self):
        val1 = val2 = 0
        self.amount_paid = 0.0
        self.amount_return = 0.0
        self.amount_tax = 0.0
        for payment in self.statement_ids:
            self.amount_paid +=  payment.amount
            self.amount_return += (payment.amount < 0 and payment.amount or 0)
        for line in self.lines:
            val1 += line.price_subtotal_incl
            val2 += line.price_subtotal
        self.amount_tax = val1-val2
        self.amount_total = val1

    #@api.onchange('amount_total','date_order','lines','partner_id', 'sequence_number',)
    def _gen_control_code(self):
      ir_sequence = self.env['ir.sequence']
      invoice_number = ir_sequence.search([('name','=','Sales Journal')]).number_next
      invoice_number = int(invoice_number)
      amount = int(self.amount_total)
      date_order = self.date_order
      date_object = datetime.strptime(date_order,'%Y-%m-%d %H:%M:%S')
      strtime = datetime.strftime(date_object,'%Y%m%d')
      authorization = self.session_id.config_id.authorization
      key = self.session_id.config_id.key
      partner_nit = self.partner_id.vat
      control_code = cc.generar(authorization,invoice_number,partner_nit,strtime,amount,key)
      print control_code
      return control_code
        
    @api.onchange('amount_total')
    def _amount_words(self):
        return num2words(self.amount_total)


    name       = fields.Char('Order Ref', required=True, readonly=True, copy=False)
    company_id = fields.Many2one('res.company', 'Company', required=True, readonly=True)
    date_order = fields.Datetime('Order Date', readonly=True, select=True)
    user_id    = fields.Many2one('res.users', 'Salesman', help="Person who uses the the cash register. It can be a reliever, a student or an interim employee.")
    amount_tax = fields.Float(compute='_amount_all', string='Taxes', digits_compute=dp.get_precision('Account'))
    amount_total    = fields.Float(compute='_amount_all', string='Total', digits_compute=dp.get_precision('Account'))
    amount_paid     = fields.Float(compute='_amount_all', string='Paid', states={'draft': [('readonly', False)]}, readonly=True, digits_compute=dp.get_precision('Account'))
    amount_return   = fields.Float(compute='_amount_all', digits_compute=dp.get_precision('Account'), multi='all') #  'Returned',
    lines           = fields.One2many('pos.order.line', 'order_id', 'Order Lines', states={'draft': [('readonly', False)]}, readonly=True, copy=True)
    statement_ids   = fields.One2many('account.bank.statement.line', 'pos_statement_id', 'Payments', states={'draft': [('readonly', False)]}, readonly=True)
    pricelist_id    = fields.Many2one('product.pricelist', 'Pricelist', required=True, states={'draft': [('readonly', False)]}, readonly=True)
    partner_id      = fields.Many2one('res.partner', 'Customer', change_default=True, select=1, states={'draft': [('readonly', False)], 'paid': [('readonly', False)]})
    sequence_number = fields.Integer('Sequence Number', help='A session-unique sequence number for the order')

    session_id = fields.Many2one('pos.session', 'Session', 
                                        #required=True,
                                        select=1,
                                        domain="[('state', '=', 'opened')]",
                                        states={'draft' : [('readonly', False)]},
                                        readonly=True)

    state = fields.Selection([('draft', 'New'),
                                   ('cancel', 'Cancelled'),
                                   ('paid', 'Paid'),
                                   ('done', 'Posted'),
                                   ('invoiced', 'Invoiced'),
                                   ('delivered', 'Delivered')],
                                  'Status', readonly=True, copy=False)

    invoice_id      = fields.Many2one('account.invoice', 'Invoice', copy=False)
    account_move    = fields.Many2one('account.move', 'Journal Entry', readonly=True, copy=False)
    picking_id      = fields.Many2one('stock.picking', 'Picking', readonly=True, copy=False)
    picking_type_id = fields.Many2one(related='session_id.config_id.picking_type_id', string="Picking Type") #, type='many2one', relation='stock.picking.type'
    location_id     = fields.Many2one(related='session_id.config_id.stock_location_id', string="Location", store=True) #, type='many2one', relation='stock.location'
    note            = fields.Text('Internal Notes')
    nb_print        = fields.Integer('Number of Print', readonly=True, copy=False)
    pos_reference   = fields.Char('Receipt Ref', readonly=True, copy=False)
    sale_journal    = fields.Many2one(related='session_id.config_id.journal_id', string='Sale Journal', store=True, readonly=True) #, relation='account.journal', type='many2one'
    control_code       = fields.Char('Control Code', readonly=True, copy=False)
    amount_words       = fields.Char('Monto', readonly=True, compute='_amount_words')
    type_of = fields.Selection([('inside', 'to go'),
                               ('outside', 'for here')],
                              'Status', readonly=True, copy=False,
                              default='inside')

    def _default_session(self, cr, uid, context=None):
        so = self.pool.get('pos.session')
        session_ids = so.search(cr, uid, [('state','=', 'opened'), ('user_id','=',uid)], context=context)
        return session_ids and session_ids[0] or False

    def _default_pricelist(self, cr, uid, context=None):
        session_ids = self._default_session(cr, uid, context) 
        if session_ids:
            session_record = self.pool.get('pos.session').browse(cr, uid, session_ids, context=context)
            return session_record.config_id.pricelist_id and session_record.config_id.pricelist_id.id or False
        return False

    def _get_out_picking_type(self, cr, uid, context=None):
        return self.pool.get('ir.model.data').xmlid_to_res_id(
                    cr, uid, 'pos_kingdom.picking_type_posout', context=context)

    _defaults = {
        'user_id': lambda self, cr, uid, context: uid,
        'state': 'draft',
        'name': '/', 
        'date_order': lambda *a: time.strftime('%Y-%m-%d %H:%M:%S'),
        'nb_print': 0,
        'sequence_number': 1,
        'session_id': _default_session,
        'company_id': lambda self,cr,uid,c: self.pool.get('res.users').browse(cr, uid, uid, c).company_id.id,
        'pricelist_id': _default_pricelist,
        'intend_for': 'table',
    }

    def create(self, cr, uid, values, context=None):
        if values.get('session_id'):
            # set name based on the sequence specified on the config
            session = self.pool['pos.session'].browse(cr, uid, values['session_id'], context=context)
            values['name'] = session.config_id.sequence_id._next()
        else:
            # fallback on any pos.order sequence
            values['name'] = self.pool.get('ir.sequence').get_id(cr, uid, 'pos.order', 'code', context=context)
        return super(pos_order, self).create(cr, uid, values, context=context)

    def test_paid(self, cr, uid, ids, context=None):
        """A Point of Sale is paid when the sum
        @return: True
        """
        for order in self.browse(cr, uid, ids, context=context):
            if order.lines and not order.amount_total:
                return True
            if (not order.lines) or (not order.statement_ids) or \
                (abs(order.amount_total-order.amount_paid) > 0.00001):
                return False
        return True

    def create_picking(self, cr, uid, ids, context=None):
        """Create a picking for each order and validate it."""
        picking_obj = self.pool.get('stock.picking')
        partner_obj = self.pool.get('res.partner')
        move_obj = self.pool.get('stock.move')

        for order in self.browse(cr, uid, ids, context=context):
            addr = order.partner_id and partner_obj.address_get(cr, uid, [order.partner_id.id], ['delivery']) or {}
            picking_type = order.picking_type_id
            picking_id = False
            if picking_type:
                picking_id = picking_obj.create(cr, uid, {
                    'origin': order.name,
                    'partner_id': addr.get('delivery',False),
                    'date_done' : order.date_order,
                    'picking_type_id': picking_type.id,
                    'company_id': order.company_id.id,
                    'move_type': 'direct',
                    'note': order.note or "",
                    'invoice_state': 'none',
                }, context=context)
                self.write(cr, uid, [order.id], {'picking_id': picking_id}, context=context)
            location_id = order.location_id.id
            if order.partner_id:
                destination_id = order.partner_id.property_stock_customer.id
            elif picking_type:
                if not picking_type.default_location_dest_id:
                    raise osv.except_osv(_('Error!'), _('Missing source or destination location for picking type %s. Please configure those fields and try again.' % (picking_type.name,)))
                destination_id = picking_type.default_location_dest_id.id
            else:
                destination_id = partner_obj.default_get(cr, uid, ['property_stock_customer'], context=context)['property_stock_customer']

            move_list = []
            for line in order.lines:
                if line.product_id and line.product_id.type == 'service':
                    continue

                move_list.append(move_obj.create(cr, uid, {
                    'name': line.name,
                    'product_uom': line.product_id.uom_id.id,
                    'product_uos': line.product_id.uom_id.id,
                    'picking_id': picking_id,
                    'picking_type_id': picking_type.id, 
                    'product_id': line.product_id.id,
                    'product_uos_qty': abs(line.qty),
                    'product_uom_qty': abs(line.qty),
                    'state': 'draft',
                    'location_id': location_id if line.qty >= 0 else destination_id,
                    'location_dest_id': destination_id if line.qty >= 0 else location_id,
                }, context=context))

            if picking_id:
                picking_obj.action_confirm(cr, uid, [picking_id], context=context)
                picking_obj.force_assign(cr, uid, [picking_id], context=context)
                picking_obj.action_done(cr, uid, [picking_id], context=context)
            elif move_list:
                move_obj.action_confirm(cr, uid, move_list, context=context)
                move_obj.force_assign(cr, uid, move_list, context=context)
                move_obj.action_done(cr, uid, move_list, context=context)
        return True

    def cancel_order(self, cr, uid, ids, context=None):
        """ Changes order state to cancel
        @return: True
        """
        stock_picking_obj = self.pool.get('stock.picking')
        for order in self.browse(cr, uid, ids, context=context):
            stock_picking_obj.action_cancel(cr, uid, [order.picking_id.id])
            if stock_picking_obj.browse(cr, uid, order.picking_id.id, context=context).state <> 'cancel':
                raise osv.except_osv(_('Error!'), _('Unable to cancel the picking.'))
        self.write(cr, uid, ids, {'state': 'cancel'}, context=context)
        return True

    def add_payment(self, cr, uid, order_id, data, context=None):
        """Create a new payment for the order"""
        context = dict(context or {})
        statement_line_obj = self.pool.get('account.bank.statement.line')
        property_obj = self.pool.get('ir.property')
        order = self.browse(cr, uid, order_id, context=context)
        args = {
            'amount': data['amount'],
            'date': data.get('payment_date', time.strftime('%Y-%m-%d')),
            'name': order.name + ': ' + (data.get('payment_name', '') or ''),
            'partner_id': order.partner_id and self.pool.get("res.partner")._find_accounting_partner(order.partner_id).id or False,
        }

        journal_id = data.get('journal', False)
        statement_id = data.get('statement_id', False)
        assert journal_id or statement_id, "No statement_id or journal_id passed to the method!"

        journal = self.pool['account.journal'].browse(cr, uid, journal_id, context=context)
        # use the company of the journal and not of the current user
        company_cxt = dict(context, force_company=journal.company_id.id)
        account_def = property_obj.get(cr, uid, 'property_account_receivable', 'res.partner', context=company_cxt)
        args['account_id'] = (order.partner_id and order.partner_id.property_account_receivable \
                             and order.partner_id.property_account_receivable.id) or (account_def and account_def.id) or False

        if not args['account_id']:
            if not args['partner_id']:
                msg = _('There is no receivable account defined to make payment.')
            else:
                msg = _('There is no receivable account defined to make payment for the partner: "%s" (id:%d).') % (order.partner_id.name, order.partner_id.id,)
            raise osv.except_osv(_('Configuration Error!'), msg)

        context.pop('pos_session_id', False)

        for statement in order.session_id.statement_ids:
            if statement.id == statement_id:
                journal_id = statement.journal_id.id
                break
            elif statement.journal_id.id == journal_id:
                statement_id = statement.id
                break

        if not statement_id:
            raise osv.except_osv(_('Error!'), _('You have to open at least one cashbox.'))

        args.update({
            'statement_id': statement_id,
            'pos_statement_id': order_id,
            'journal_id': journal_id,
            'ref': order.session_id.name,
        })

        statement_line_obj.create(cr, uid, args, context=context)

        return statement_id

    def refund(self, cr, uid, ids, context=None):
        """Create a copy of order  for refund order"""
        clone_list = []
        line_obj = self.pool.get('pos.order.line')

        for order in self.browse(cr, uid, ids, context=context):
            current_session_ids = self.pool.get('pos.session').search(cr, uid, [
                ('state', '!=', 'closed'),
                ('user_id', '=', uid)], context=context)
            if not current_session_ids:
                raise osv.except_osv(_('Error!'), _('To return product(s), you need to open a session that will be used to register the refund.'))

            clone_id = self.copy(cr, uid, order.id, {
                'name': order.name + ' REFUND', # not used, name forced by create
                'session_id': current_session_ids[0],
                'date_order': time.strftime('%Y-%m-%d %H:%M:%S'),
            }, context=context)
            clone_list.append(clone_id)

        for clone in self.browse(cr, uid, clone_list, context=context):
            for order_line in clone.lines:
                line_obj.write(cr, uid, [order_line.id], {
                    'qty': -order_line.qty
                }, context=context)

        abs = {
            'name': _('Return Products'),
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'pos.order',
            'res_id':clone_list[0],
            'view_id': False,
            'context':context,
            'type': 'ir.actions.act_window',
            'nodestroy': True,
            'target': 'current',
        }
        return abs

    def action_invoice_state(self, cr, uid, ids, context=None):
        return self.write(cr, uid, ids, {'state':'invoiced'}, context=context)

    def action_invoice(self, cr, uid, ids, context=None):
        inv_ref = self.pool.get('account.invoice')
        inv_line_ref = self.pool.get('account.invoice.line')
        product_obj = self.pool.get('product.product')
        inv_ids = []

        for order in self.pool.get('pos.order').browse(cr, uid, ids, context=context):
            if order.invoice_id:
                inv_ids.append(order.invoice_id.id)
                continue

            if not order.partner_id:
                raise osv.except_osv(_('Error!'), _('Please provide a partner for the sale.'))

            acc = order.partner_id.property_account_receivable.id
            inv = {
                'name': order.name,
                'origin': order.name,
                'account_id': acc,
                'journal_id': order.sale_journal.id or None,
                'type': 'out_invoice',
                'reference': order.name,
                'partner_id': order.partner_id.id,
                'comment': order.note or '',
                'currency_id': order.pricelist_id.currency_id.id, # considering partner's sale pricelist's currency
                'control_code':order._gen_control_code(),
            }
            inv.update(inv_ref.onchange_partner_id(cr, uid, [], 'out_invoice', order.partner_id.id)['value'])
            if not inv.get('account_id', None):
                inv['account_id'] = acc
            inv_id = inv_ref.create(cr, uid, inv, context=context)

            self.write(cr, uid, [order.id], {'invoice_id': inv_id, 'state': 'invoiced'}, context=context)
            inv_ids.append(inv_id)
            for line in order.lines:
                inv_line = {
                    'invoice_id': inv_id,
                    'product_id': line.product_id.id,
                    'quantity': line.qty,
                }
                inv_name = product_obj.name_get(cr, uid, [line.product_id.id], context=context)[0][1]
                inv_line.update(inv_line_ref.product_id_change(cr, uid, [],
                                                               line.product_id.id,
                                                               line.product_id.uom_id.id,
                                                               line.qty, partner_id = order.partner_id.id,
                                                               fposition_id=order.partner_id.property_account_position.id)['value'])
                inv_line['price_unit'] = line.price_unit
                inv_line['discount'] = line.discount
                inv_line['name'] = inv_name
                inv_line['invoice_line_tax_id'] = [(6, 0, [x.id for x in line.product_id.taxes_id] )]
                inv_line_ref.create(cr, uid, inv_line, context=context)
            inv_ref.button_reset_taxes(cr, uid, [inv_id], context=context)
            self.signal_workflow(cr, uid, [order.id], 'invoice')
            inv_ref.signal_workflow(cr, uid, [inv_id], 'validate')

        if not inv_ids: return {}

        mod_obj = self.pool.get('ir.model.data')
        res = mod_obj.get_object_reference(cr, uid, 'account', 'invoice_form')
        res_id = res and res[1] or False
        return {
            'name': _('Customer Invoice'),
            'view_type': 'form',
            'view_mode': 'form',
            'view_id': [res_id],
            'res_model': 'account.invoice',
            'context': "{'type':'out_invoice'}",
            'type': 'ir.actions.act_window',
            'nodestroy': True,
            'target': 'current',
            'res_id': inv_ids and inv_ids[0] or False,
        }

    def create_account_move(self, cr, uid, ids, context=None):
        return self._create_account_move_line(cr, uid, ids, None, None, context=context)

    def _prepare_analytic_account(self, cr, uid, line, context=None):
        '''This method is designed to be inherited in a custom module'''
        return False

    def _create_account_move_line(self, cr, uid, ids, session=None, move_id=None, context=None):
        # Tricky, via the workflow, we only have one id in the ids variable
        """Create a account move line of order grouped by products or not."""
        account_move_obj = self.pool.get('account.move')
        account_period_obj = self.pool.get('account.period')
        account_tax_obj = self.pool.get('account.tax')
        property_obj = self.pool.get('ir.property')
        cur_obj = self.pool.get('res.currency')

        #session_ids = set(order.session_id for order in self.browse(cr, uid, ids, context=context))

        if session and not all(session.id == order.session_id.id for order in self.browse(cr, uid, ids, context=context)):
            raise osv.except_osv(_('Error!'), _('Selected orders do not have the same session!'))

        grouped_data = {}
        have_to_group_by = session and session.config_id.group_by or False

        def compute_tax(amount, tax, line):
            if amount > 0:
                tax_code_id = tax['base_code_id']
                tax_amount = line.price_subtotal * tax['base_sign']
            else:
                tax_code_id = tax['ref_base_code_id']
                tax_amount = line.price_subtotal * tax['ref_base_sign']

            return (tax_code_id, tax_amount,)

        for order in self.browse(cr, uid, ids, context=context):
            if order.account_move:
                continue
            if order.state != 'paid':
                continue

            current_company = order.sale_journal.company_id

            group_tax = {}
            account_def = property_obj.get(cr, uid, 'property_account_receivable', 'res.partner', context=context)

            order_account = order.partner_id and \
                            order.partner_id.property_account_receivable and \
                            order.partner_id.property_account_receivable.id or \
                            account_def and account_def.id or current_company.account_receivable.id

            if move_id is None:
                # Create an entry for the sale
                move_id = account_move_obj.create(cr, uid, {
                    'ref' : order.name,
                    'journal_id': order.sale_journal.id,
                }, context=context)

            def insert_data(data_type, values):
                # if have_to_group_by:

                sale_journal_id = order.sale_journal.id
                period = account_period_obj.find(cr, uid, context=dict(context or {}, company_id=current_company.id))[0]

                # 'quantity': line.qty,
                # 'product_id': line.product_id.id,
                values.update({
                    'date': order.date_order[:10],
                    'ref': order.name,
                    'partner_id': order.partner_id and self.pool.get("res.partner")._find_accounting_partner(order.partner_id).id or False,
                    'journal_id' : sale_journal_id,
                    'period_id' : period,
                    'move_id' : move_id,
                    'company_id': current_company.id,
                })

                if data_type == 'product':
                    key = ('product', values['partner_id'], values['product_id'], values['analytic_account_id'], values['debit'] > 0)
                elif data_type == 'tax':
                    key = ('tax', values['partner_id'], values['tax_code_id'], values['debit'] > 0)
                elif data_type == 'counter_part':
                    key = ('counter_part', values['partner_id'], values['account_id'], values['debit'] > 0)
                else:
                    return

                grouped_data.setdefault(key, [])

                # if not have_to_group_by or (not grouped_data[key]):
                #     grouped_data[key].append(values)
                # else:
                #     pass

                if have_to_group_by:
                    if not grouped_data[key]:
                        grouped_data[key].append(values)
                    else:
                        current_value = grouped_data[key][0]
                        current_value['quantity'] = current_value.get('quantity', 0.0) +  values.get('quantity', 0.0)
                        current_value['credit'] = current_value.get('credit', 0.0) + values.get('credit', 0.0)
                        current_value['debit'] = current_value.get('debit', 0.0) + values.get('debit', 0.0)
                        current_value['tax_amount'] = current_value.get('tax_amount', 0.0) + values.get('tax_amount', 0.0)
                else:
                    grouped_data[key].append(values)

            #because of the weird way the pos order is written, we need to make sure there is at least one line, 
            #because just after the 'for' loop there are references to 'line' and 'income_account' variables (that 
            #are set inside the for loop)
            #TOFIX: a deep refactoring of this method (and class!) is needed in order to get rid of this stupid hack
            assert order.lines, _('The POS order must have lines when calling this method')
            # Create an move for each order line

            cur = order.pricelist_id.currency_id
            for line in order.lines:
                tax_amount = 0
                taxes = []
                for t in line.product_id.taxes_id:
                    if t.company_id.id == current_company.id:
                        taxes.append(t)
                computed_taxes = account_tax_obj.compute_all(cr, uid, taxes, line.price_unit * (100.0-line.discount) / 100.0, line.qty)['taxes']

                for tax in computed_taxes:
                    tax_amount += cur_obj.round(cr, uid, cur, tax['amount'])
                    group_key = (tax['tax_code_id'], tax['base_code_id'], tax['account_collected_id'], tax['id'])

                    group_tax.setdefault(group_key, 0)
                    group_tax[group_key] += cur_obj.round(cr, uid, cur, tax['amount'])

                amount = line.price_subtotal

                # Search for the income account
                if  line.product_id.property_account_income.id:
                    income_account = line.product_id.property_account_income.id
                elif line.product_id.categ_id.property_account_income_categ.id:
                    income_account = line.product_id.categ_id.property_account_income_categ.id
                else:
                    raise osv.except_osv(_('Error!'), _('Please define income '\
                        'account for this product: "%s" (id:%d).') \
                        % (line.product_id.name, line.product_id.id, ))

                # Empty the tax list as long as there is no tax code:
                tax_code_id = False
                tax_amount = 0
                while computed_taxes:
                    tax = computed_taxes.pop(0)
                    tax_code_id, tax_amount = compute_tax(amount, tax, line)

                    # If there is one we stop
                    if tax_code_id:
                        break

                # Create a move for the line
                insert_data('product', {
                    'name': line.product_id.name,
                    'quantity': line.qty,
                    'product_id': line.product_id.id,
                    'account_id': income_account,
                    'analytic_account_id': self._prepare_analytic_account(cr, uid, line, context=context),
                    'credit': ((amount>0) and amount) or 0.0,
                    'debit': ((amount<0) and -amount) or 0.0,
                    'tax_code_id': tax_code_id,
                    'tax_amount': tax_amount,
                    'partner_id': order.partner_id and self.pool.get("res.partner")._find_accounting_partner(order.partner_id).id or False
                })

                # For each remaining tax with a code, whe create a move line
                for tax in computed_taxes:
                    tax_code_id, tax_amount = compute_tax(amount, tax, line)
                    if not tax_code_id:
                        continue

                    insert_data('tax', {
                        'name': _('Tax'),
                        'product_id':line.product_id.id,
                        'quantity': line.qty,
                        'account_id': income_account,
                        'credit': 0.0,
                        'debit': 0.0,
                        'tax_code_id': tax_code_id,
                        'tax_amount': tax_amount,
                        'partner_id': order.partner_id and self.pool.get("res.partner")._find_accounting_partner(order.partner_id).id or False
                    })

            # Create a move for each tax group
            (tax_code_pos, base_code_pos, account_pos, tax_id)= (0, 1, 2, 3)

            for key, tax_amount in group_tax.items():
                tax = self.pool.get('account.tax').browse(cr, uid, key[tax_id], context=context)
                insert_data('tax', {
                    'name': _('Tax') + ' ' + tax.name,
                    'quantity': line.qty,
                    'product_id': line.product_id.id,
                    'account_id': key[account_pos] or income_account,
                    'credit': ((tax_amount>0) and tax_amount) or 0.0,
                    'debit': ((tax_amount<0) and -tax_amount) or 0.0,
                    'tax_code_id': key[tax_code_pos],
                    'tax_amount': tax_amount,
                    'partner_id': order.partner_id and self.pool.get("res.partner")._find_accounting_partner(order.partner_id).id or False
                })

            # counterpart
            insert_data('counter_part', {
                'name': _("Trade Receivables"), #order.name,
                'account_id': order_account,
                'credit': ((order.amount_total < 0) and -order.amount_total) or 0.0,
                'debit': ((order.amount_total > 0) and order.amount_total) or 0.0,
                'partner_id': order.partner_id and self.pool.get("res.partner")._find_accounting_partner(order.partner_id).id or False
            })

            order.write({'state':'done', 'account_move': move_id})

        all_lines = []
        for group_key, group_data in grouped_data.iteritems():
            for value in group_data:
                all_lines.append((0, 0, value),)
        if move_id: #In case no order was changed
            self.pool.get("account.move").write(cr, uid, [move_id], {'line_id':all_lines}, context=context)

        return True

    def action_payment(self, cr, uid, ids, context=None):
        return self.write(cr, uid, ids, {'state': 'payment'}, context=context)

    def action_paid(self, cr, uid, ids, context=None):
        self.write(cr, uid, ids, {'state': 'paid'}, context=context)
        self.create_picking(cr, uid, ids, context=context)
        return True

    def action_cancel(self, cr, uid, ids, context=None):
        self.write(cr, uid, ids, {'state': 'cancel'}, context=context)
        return True

    def action_deliver(self, cr, uid, ids, context=None):
        self.write(cr, uid, ids, {'state': 'delivered'}, context=context)
        return True

    def action_done(self, cr, uid, ids, context=None):
        self.create_account_move(cr, uid, ids, context=context)
        return True

class account_bank_statement(models.Model):
    _inherit = 'account.bank.statement'
    user_id = fields.Many2one('res.users', 'User', readonly=True)
    _defaults = {
        'user_id': lambda self,cr,uid,c={}: uid
    }

class account_bank_statement_line(models.Model):
    _inherit = 'account.bank.statement.line'
    pos_statement_id = fields.Many2one('pos.order', ondelete='cascade')


class pos_order_line(models.Model):
    _name = "pos.order.line"
    _description = "Lines of Point of Sale"
    _rec_name = "product_id"

    @api.one
    @api.depends('qty','order_id','product_id','price_unit','discount')
    def _amount_line_all(self):
        account_tax_obj = self.env['account.tax']
        taxes_ids = [ tax for tax in self.product_id.taxes_id if tax.company_id.id == self.order_id.company_id.id ]
        price = self.price_unit * (1 - (self.discount or 0.0) / 100.0)
        taxes = account_tax_obj.compute_all(price, self.qty, self.product_id, self.order_id.partner_id or False, False)
        #[FIXME] This should rounding to 
        #currency_id from self.env['res.currency'].
        currency =  self.order_id.session_id.currency_id
        self.price_subtotal = currency.round(taxes['total'])
        self.price_subtotal_incl = currency.round(taxes['total_included'])

    def onchange_product_id(self, cr, uid, ids, pricelist, product_id, qty=0, partner_id=False, context=None):
       context = context or {}
       if not product_id:
            return {}
       if not pricelist:
           raise osv.except_osv(_('No Pricelist!'),
               _('You have to select a pricelist in the sale form !\n' \
               'Please set one before choosing a product.'))

       price = self.pool.get('product.pricelist').price_get(cr, uid, [pricelist],
               product_id, qty or 1.0, partner_id)[pricelist]

       result = self.onchange_qty(cr, uid, ids, product_id, 0.0, qty, price, context=context)
       result['value']['price_unit'] = price
       return result

    def onchange_qty(self, cr, uid, ids, product, discount, qty, price_unit, context=None):
        result = {}
        if not product:
            return result
        account_tax_obj = self.pool.get('account.tax')
        cur_obj = self.pool.get('res.currency')

        prod = self.pool.get('product.product').browse(cr, uid, product, context=context)

        price = price_unit * (1 - (discount or 0.0) / 100.0)
        taxes = account_tax_obj.compute_all(cr, uid, prod.taxes_id, price, qty, product=prod, partner=False)

        result['price_subtotal'] = taxes['total']
        result['price_subtotal_incl'] = taxes['total_included']
        return {'value': result}

    company_id = fields.Many2one('res.company', 'Company', required=True)
    name = fields.Char('Line No', required=True, copy=False)
    notice = fields.Char('Discount Notice')
    product_id = fields.Many2one('product.product', 'Product', domain=[('sale_ok', '=', True)], required=True, change_default=True)
    price_unit = fields.Float(string='Unit Price', digits_compute=dp.get_precision('Account'))
    qty = fields.Float('Quantity', digits_compute=dp.get_precision('Product UoS'))
    price_subtotal = fields.Float(compute='_amount_line_all', multi='pos_order_line_amount', digits_compute=dp.get_precision('Account'), string='Subtotal w/o Tax', store=True)
    price_subtotal_incl = fields.Float(compute='_amount_line_all', multi='pos_order_line_amount', digits_compute=dp.get_precision('Account'), string='Subtotal', store=True)
    discount = fields.Float('Discount (%)', digits_compute=dp.get_precision('Account'))
    order_id = fields.Many2one('pos.order', 'Order Ref', ondelete='cascade')
    create_date = fields.Datetime('Creation Date', readonly=True)
    type_of = fields.Selection([('inside', 'to go'),
                               ('outside', 'for here')],
                              'Status', readonly=True, copy=False,
                              default='inside')

    _defaults = {
        'name': lambda obj, cr, uid, context: obj.pool.get('ir.sequence').get(cr, uid, 'pos.order.line'),
        'qty': lambda *a: 1,
        'discount': lambda *a: 0.0,
        'company_id': lambda self,cr,uid,c: self.pool.get('res.users').browse(cr, uid, uid, c).company_id.id,
    }

class ean_wizard(models.TransientModel):
    _name = 'pos.ean_wizard'
    ean13_pattern = fields.Char('Reference', size=13, required=True, translate=True)
    def sanitize_ean13(self, cr, uid, ids, context):
        for r in self.browse(cr,uid,ids):
            ean13 = openerp.addons.product.product.sanitize_ean13(r.ean13_pattern)
            m = context.get('active_model')
            m_id =  context.get('active_id')
            self.pool[m].write(cr,uid,[m_id],{'ean13':ean13})
        return { 'type' : 'ir.actions.act_window_close' }

class pos_category(models.Model):
    _name = "pos.category"
    _description = "Public Category"
    _order = "sequence, name"

    _constraints = [
        (models.Model._check_recursion, 'Error ! You cannot create recursive categories.', ['parent_id'])
    ]

    def name_get(self, cr, uid, ids, context=None):
        res = []
        for cat in self.browse(cr, uid, ids, context=context):
            names = [cat.name]
            pcat = cat.parent_id
            while pcat:
                names.append(pcat.name)
                pcat = pcat.parent_id
            res.append((cat.id, ' / '.join(reversed(names))))
        return res

    def _name_get_fnc(self, cr, uid, ids, context=None):
        res = self.name_get(cr, uid, ids, context=context)
        return dict(res)

    name = fields.Char('Name', required=True, translate=True)
    complete_name = fields.Char(compute='_name_get_fnc', string='Name')
    parent_id = fields.Many2one('pos.category','Parent Category', select=True)
    child_id = fields.One2many('pos.category', 'parent_id', string='Children Categories')
    sequence = fields.Integer('Sequence', help="Gives the sequence order when displaying a list of product categories.")
    image = fields.Binary("Image",
            help="This field holds the image used as image for the cateogry, limited to 1024x1024px.")
    image_medium = fields.Binary(compute='_get_image',
            string="Medium-sized image",
            store=True,
            help="Medium-sized image of the category. It is automatically "\
                 "resized as a 128x128px image, with aspect ratio preserved. "\
                 "Use this field in form views or some kanban views.")
    image_small = fields.Binary(compute='_get_image',
            string="Small-sized image",
            store=True,
            help="Small-sized image of the category. It is automatically "\
                 "resized as a 64x64px image, with aspect ratio preserved. "\
                 "Use this field anywhere a small image is required.")

    @api.depends('image')
    def _get_image(self):
        for record in self:
            if record.image:
                record.image_medium = crop_image(record.image, thumbnail_ratio=3)
                record.image_thumb = crop_image(record.image, thumbnail_ratio=4)
            else:
                record.image_medium = False
                record.iamge_thumb = False


class product_attribute_value(models.Model):
    _inherit = 'product.attribute.value'

    def _get_image(self, cr, uid, ids, name, args, context=None):
        result = dict.fromkeys(ids, False)
        for obj in self.browse(cr, uid, ids, context=context):
            result[obj.id] = tools.image_get_resized_images(obj.image)
        return result

    def _set_image(self, cr, uid, id, name, value, args, context=None):
        return self.write(cr, uid, [id], {'image': tools.image_resize_image_big(value)}, context=context)

    image = fields.Binary("Image",help="This field holds the image used as image for the attribute value, limited to 1024x1024px.")
    image_medium = fields.Binary(compute='_get_image', inverse='_set_image', string="Medium-sized image", multi="_get_image",
        store={
            'product.attribute.value': (lambda self, cr, uid, ids, c={}: ids, ['image'], 10)
        },
        help="Medium-sized image of the attribute value, It is automatically "\
             "resized as a 128x128px image, with aspect ratio preserved. "\
             "Use this field in form views or some kanban views.")

    image_small = fields.Binary(compute='_get_image', inverse='_set_image', string="Small-sized image", multi="_get_image",
        store={
            'product.attribute.value': (lambda self, cr, uid, ids, c={}: ids, ['image'], 10)
        },
        help="Small-sized image of the attribute value, It is automatically "\
             "resized as a 64x64px image, with aspect ratio preserved. "\
             "Use this field anywhere a small image is required.")

class product_template(models.Model):
    _inherit = 'product.template'

    income_pdt       = fields.Boolean('Point of Sale Cash In',
        help="Check if, this is a product you can use to put cash into a statement for the point of sale backend.")
    expense_pdt      = fields.Boolean('Point of Sale Cash Out',
        help="Check if, this is a product you can use to take cash from a statement for the point of sale backend, example: money lost, transfer to bank, etc.")
    available_in_pos = fields.Boolean('Available in the Point of Sale',
        help='Check if you want this product to appear in the Point of Sale')
    to_weight        = fields.Boolean('To Weigh With Scale',
        help="Check if the product should be weighted using the hardware scale integration")
    pos_categ_id     = fields.Many2one('pos.category','Point of Sale Category',
        help="Those categories are used to group similar products for point of sale.")
    is_combo = fields.Boolean('Point of Sale Combo')

    _defaults = {
        'to_weight' : False,
        'available_in_pos': True,
    }

    def unlink(self, cr, uid, ids, context=None):
        product_ctx = dict(context or {}, active_test=False)
        if self.search_count(cr, uid, [('id', 'in', ids), ('available_in_pos', '=', True)], context=product_ctx):
            if self.pool['pos.session'].search_count(cr, uid, [('state', '!=', 'closed')], context=context):
                raise osv.except_osv(_('Error!'),
                    _('You cannot delete a product saleable in point of sale while a session is still opened.'))
        return super(product_template, self).unlink(cr, uid, ids, context=context)

class res_partner(models.Model):
    _inherit = 'res.partner'

    def create_from_ui(self, cr, uid, partner, context=None):
        """ create or modify a partner from the point of sale ui.
            partner contains the partner's fields. """

        #image is a dataurl, get the data after the comma
        if partner.get('image',False):
            img =  partner['image'].split(',')[1]
            partner['image'] = img

        if partner.get('id',False):  # Modifying existing partner
            partner_id = partner['id']
            del partner['id']
            self.write(cr, uid, [partner_id], partner, context=context)
        else:
            partner_id = self.create(cr, uid, partner, context=context)

        return partner_id

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
