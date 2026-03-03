"""
integrations/README.md content — see README.md in this folder for details.
"""
# Este módulo expone 3 clientes de APIs externas:
#   - StripeClient: pagos internacionales (principal)
#   - MercadoPagoClient: pagos regionales (alternativa)
#   - ARCAClient: facturación electrónica AFIP/ARCA (Argentina)
#
# Ninguno contiene lógica de negocio.
# Toda lógica de activación/desactivación vive en services/payment_services.py
