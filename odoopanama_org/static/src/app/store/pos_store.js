/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { PosStore } from "@point_of_sale/app/store/pos_store";
import { AlertDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import { _t } from "@web/core/l10n/translation";

patch(PosStore.prototype, {
    /**
     * Validaciones antes de ir a PaymentScreen
     */
    async pay() {
        const currentOrder = this.get_order();

        if (!currentOrder) {
            return super.pay(...arguments);
        }

        // Validar cliente obligatorio
        if (!currentOrder.get_partner()) {
            this.env.services.dialog.add(AlertDialog, {
                title: _t("Cliente requerido"),
                body: _t("Debe seleccionar o registrar un cliente."),
            });
            return;
        }

        // Validar precios y cantidades de productos
        for (const line of currentOrder.get_orderlines()) {
            const price = line.get_unit_price();
            const qty = line.get_quantity();
            const discount = line.get_discount();

            if ((price === 0 || qty === 0) && discount !== 100) {
                this.env.services.dialog.add(AlertDialog, {
                    title: _t("Producto inválido"),
                    body: _t("El producto '%s' tiene precio o cantidad en cero.", line.get_product().display_name),
                });
                return;
            }
        }

        return super.pay(...arguments);
    },
});
