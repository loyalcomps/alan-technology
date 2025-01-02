# -*- coding: utf-8 -*-
# from odoo import http


# class PdcPayment(http.Controller):
#     @http.route('/pdc_payment/pdc_payment', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/pdc_payment/pdc_payment/objects', auth='public')
#     def list(self, **kw):
#         return http.request.render('pdc_payment.listing', {
#             'root': '/pdc_payment/pdc_payment',
#             'objects': http.request.env['pdc_payment.pdc_payment'].search([]),
#         })

#     @http.route('/pdc_payment/pdc_payment/objects/<model("pdc_payment.pdc_payment"):obj>', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('pdc_payment.object', {
#             'object': obj
#         })
