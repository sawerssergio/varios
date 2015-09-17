# -*- coding: utf-8 -*-
{
    'name': 'POS Kingdom',
    'version': '1.0.1',
    'category': 'Point Of Sale',
    'sequence': 6,
    'summary': 'Punto de Venta Chicken\'s Kingdom',
    'description': """
Quick and Easy sale process
===========================

This module allows you to manage your shop sales very easily with a fully web based touchscreen interface.
It is compatible with all PC tablets and the iPad, offering multiple payment methods. 

Product selection can be done in several ways: 

* Using a barcode reader
* Browsing through categories of products or via a text search.

Main Features
-------------
* Fast encoding of the sale
* Choose one payment method (the quick way) or split the payment between several payment methods
* Computation of the amount of money to return
* Create and confirm the picking list automatically
* Allows the user to create an invoice automatically
* Refund previous sales
    """,
    'author': 'Sawers',
    'depends': ['sale_stock'],
    'data': [
        'data/report_paperformat.xml',
        'security/pos_kingdom_security.xml',
        'security/ir.model.access.csv',
        'wizard/pos_box.xml',
        'wizard/pos_confirm.xml',
        'wizard/pos_details.xml',
        'wizard/pos_discount.xml',
        'wizard/pos_open_statement.xml',
        'wizard/pos_payment.xml',
        'wizard/pos_session_opening.xml',
        'views/templates.xml',
        'pos_kingdom_report.xml',
        'pos_kingdom_view.xml',
        'pos_kingdom_cashbox.xml',
        'res_company_view.xml',
        'pos_kingdom_sequence.xml',
        'pos_kingdom_data.xml',
        'report/pos_order_report_view.xml',
        'pos_kingdom_workflow.xml',
        'account_statement_view.xml',
        'account_statement_report.xml',
        'res_users_view.xml',
        'res_partner_view.xml',
        'views/report_statement.xml',
        'views/report_usersproduct.xml',
        'views/report_receipt.xml',
        'views/report_saleslines.xml',
        'views/report_detailsofsales.xml',
        'views/report_payment.xml',
        'views/report_sessionsummary.xml',
        'views/report_invoice.xml',
        'views/pos_kingdom.xml',
        'views/report_cashcount.xml',
        'data/kingdom_data.xml',
    ],
    'demo': [
        'data/kingdom_data.xml',
    ],
    'installable': True,
    'application': True,
    'qweb': ['static/src/xml/pos.xml'],
    'auto_install': False,
}

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
