Usar la API de Stripe directamente desde tu backend/servidor (por ejemplo, generar un Stripe Checkout y redireccionar).
Usar un paquete de la comunidad como st-paywall, que facilita añadir un paywall con Stripe.
Integrar un componente custom (ej. streamlit_stripe_card) para capturar tarjetas y tokens.
There is no official built-in Stripe integration in Streamlit itself — todas las implementaciones se apoyan en llamadas a la API de Stripe, almacenamiento de estados y lógica propia.
Ejemplo comunitario: st-paywall
La librería st-paywall permite configurar un paywall simple usando Stripe:
Agrega un botón de pago dentro del sidebar o UI.
Usa links de Stripe (Checkout) y claves de API configuradas en .streamlit/secrets.toml.
Verifica si el usuario está ‘subscribed’ o no antes de mostrar contenido.
No es parte de Streamlit oficial, pero está basado en API de Stripe y funciona con el sistema de autenticación de Streamlit.
Requisitos de integración de Stripe con Streamlit
Para implementar Stripe correctamente:
Generar un Checkout Session desde backend (puede estar en una función externa o servidor).
Redireccionar al usuario a Stripe Payment Page.
Usar webhooks para recibir eventos (pago completado) y actualizar el estado almacenado (por ejemplo en Supabase).
En Streamlit, validar si el usuario ya pagó para mostrar contenido.
Esto sí es compatible y practicable.
🟡 Integración de MercadoPago
Ni la documentación oficial de MercadoPago ni la de Streamlit mencionan una integración nativa para Streamlit.
Qué se puede hacer
MercadoPago tiene APIs completas para integrar pagos con distintos métodos (checkout, medios locales, etc.), pero no hay un “componente MercadoPago” para Streamlit publicado en la documentación ni en paquetes comunitarios populares.
La integración con MercadoPago tendría que hacerse de esta forma:
Crear sesión de pago con API de MercadoPago (Checkout API).
Redireccionar a la página de pago.
Recibir la confirmación (webhook o callback).
Almacenar en tu backend el estado de pago.
Mostrar contenido en Streamlit según ese estado.
Esto significa que sí es técnicamente posible, pero no con soporte nativo del framework.
📌 Comparación rápida de compatibilidad
Método de pago	Soporte nativo en Streamlit	Requiere API externa	Plugins/paquetes comunitarios
Stripe	❌	✔️	✔️ (st-paywall, streamlit_stripe_card)
MercadoPago	❌	✔️	❌ no oficial
Otros métodos (PayPal, MercadoPago etc.)	❌	✔️	❌
Conclusión: Streamlit no tiene métodos de pago integrados.
La forma funcional de incorporar pagos es conectando a APIs externas (Stripe, MercadoPago, etc.) y gestionando la lógica de negocio en tu código, backend o funciones serverless.
🧩 Diferencias clave de integración
Stripe
API madura, bien documentada.
Permite Checkout Sessions, Billing, Subscriptions.
Puede integrarse fácilmente usando webhooks y sesiones.
MercadoPago
Puede integrarse con APIs de pago (Checkout API).
No hay componentes comunitarios listos para Streamlit.
Necesita implementar lógica de sesión y confirmación por tu cuenta.
🛠 Recomendación técnica para tu proyecto
Si tu objetivo es un MVP con pagos recurrentes o one-time dentro de Streamlit:
Stripe es la opción más fácil y práctica, porque:
Tiene bibliotecas bien soportadas.
Puede generar enlaces de pago y manejar suscripciones.
La comunidad ya ha creado integraciones tipo paywall.
MercadoPago también puede usarse, pero:
Requiere implementación personalizada usando su API.
La lógica de sesión/pago debe manejarse completamente por tu backend o funciones serverless.
🧠 Resumen
Streamlit no ofrece soporte de pago nativo.
Stripe sí es integrable, usando su API oficial o paquetes como st-paywall.
MercadoPago también puede integrarse, pero sin componentes existentes; requerirá lógica propia usando su API.
En ambos casos, la app Streamlit manejará la UI, pero la lógica de pago y la confirmación de estado deben ser gestionadas por APIs externas y webhooks.