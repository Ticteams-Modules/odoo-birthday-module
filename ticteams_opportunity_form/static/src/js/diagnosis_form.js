/* ==========================================================================
   TicTeams · Odoo Diagnosis Form  -  standalone step engine
   ========================================================================== */
(function () {
    "use strict";

    var root = document.getElementById("diag-root");
    var PREFILL = {
        name: (root && root.dataset.name) || "",
        email: (root && root.dataset.email) || "",
        phone: (root && root.dataset.phone) || "",
        company: (root && root.dataset.company) || "",
    };

    // ----------------------------------------------------------------------
    // Step configuration. Field keys map 1:1 to crm.lead fields.
    // type: intro | single | multi | text | fields | contact | done
    // ----------------------------------------------------------------------
    var STEPS = [
        {
            type: "single",
            field: "x_diag_industry",
            required: true,
            question: "¿En qué sector opera tu empresa?",
            help: "Elige la opción que mejor describa tu negocio.",
            cols: 2,
            options: [
                ["distribution", "Distribución / Comercio"],
                ["manufacturing", "Fabricación / Producción"],
                ["professional_services", "Servicios profesionales"],
                ["retail", "Retail / Tienda"],
                ["construction", "Construcción"],
                ["health", "Salud"],
                ["other", "Otro"],
            ],
        },
        {
            type: "single",
            field: "x_diag_company_size",
            required: true,
            question: "¿Cuántas personas trabajan en tu empresa?",
            help: "Esto nos ayuda a dimensionar la implementación.",
            cols: 2,
            options: [
                ["5_15", "De 5 a 15 personas"],
                ["16_30", "De 16 a 30 personas"],
                ["31_80", "De 31 a 80 personas"],
                ["81_200", "De 81 a 200 personas"],
                ["200_plus", "Más de 200 personas"],
            ],
        },
        {
            type: "multi",
            required: true,
            question: "¿Cómo gestionas tu operación hoy?",
            help: "Selecciona todas las que apliquen.",
            cols: 1,
            options: [
                ["x_diag_mgmt_excel", "Excel y hojas de cálculo"],
                ["x_diag_mgmt_basic_accounting", "Software contable básico"],
                ["x_diag_mgmt_disconnected", "Herramientas desconectadas"],
                ["x_diag_mgmt_existing_erp", "Tengo un ERP pero quiero cambiar"],
                ["x_diag_mgmt_none", "Aún sin un sistema claro"],
            ],
        },
        {
            type: "fields",
            question: "¿Dónde operas y qué necesitas migrar?",
            help: "El país determina la configuración fiscal y la facturación electrónica.",
            inputs: [
                { key: "x_diag_country", kind: "text", required: true,
                  label: "País de operación" },
                { key: "x_diag_migration_notes", kind: "textarea",
                  label: "Software y datos actuales a migrar (opcional)" },
            ],
        },
        {
            type: "multi",
            required: true,
            question: "¿Qué módulos de Odoo necesitas configurar?",
            help: "Selecciona todos los que apliquen.",
            cols: 2,
            options: [
                ["x_diag_mod_sales_crm", "Ventas y CRM"],
                ["x_diag_mod_inventory", "Inventario y almacén"],
                ["x_diag_mod_purchase", "Compras y proveedores"],
                ["x_diag_mod_accounting", "Contabilidad y facturación"],
                ["x_diag_mod_hr", "Recursos humanos"],
                ["x_diag_mod_manufacturing", "Fabricación / MRP"],
                ["x_diag_mod_projects", "Proyectos"],
                ["x_diag_mod_pos", "Punto de venta"],
                ["x_diag_mod_ecommerce", "Sitio web / Comercio electrónico"],
                ["x_diag_mod_other", "Otro"],
            ],
        },
        {
            type: "fields",
            question: "¿Necesitas desarrollo a medida?",
            help: "Más allá de la configuración estándar de Odoo.",
            inputs: [
                { key: "x_diag_custom_modules", kind: "select", required: true,
                  label: "Módulos a medida", options: [
                    ["yes", "Sí, necesito módulos a medida"],
                    ["maybe", "Quizás / aún no estoy seguro"],
                    ["no", "No, Odoo estándar es suficiente"],
                  ] },
                { key: "x_diag_custom_modules_desc", kind: "textarea",
                  label: "Describe brevemente las necesidades a medida (opcional)" },
            ],
        },
        {
            type: "fields",
            question: "¿Cómo está tu contabilidad y facturación electrónica?",
            help: "Cuéntanos qué tienes en marcha y qué hay que construir.",
            inputs: [
                { key: "x_diag_accounting_status", kind: "select", required: true,
                  label: "Estado de la contabilidad", options: [
                    ["developed", "Ya desarrollada / localizada"],
                    ["partial", "Configurada parcialmente"],
                    ["needs_dev", "Necesita desarrollarse"],
                    ["none", "Aún no uso contabilidad"],
                  ] },
                { key: "x_diag_einvoice_provider", kind: "text",
                  label: "Proveedor de facturación electrónica (actual o preferido, opcional)" },
                { key: "x_diag_fiscal_docs", kind: "textarea",
                  label: "Documentos fiscales que necesitas emitir (opcional)" },
            ],
        },
        {
            type: "fields",
            question: "Punto de venta y monedas",
            help: "Deja en blanco lo que no aplique.",
            inputs: [
                { key: "x_diag_pos_count", kind: "number",
                  label: "Número de puntos de venta físicos" },
                { key: "x_diag_pos_hardware", kind: "select",
                  label: "Integración de hardware en el POS", options: [
                    ["yes", "Sí, necesita hardware (impresora, lector, cajón)"],
                    ["no", "No necesita hardware"],
                    ["na", "No aplica"],
                  ] },
                { key: "x_diag_multi_currency", kind: "select",
                  label: "Multimoneda", options: [
                    ["yes", "Sí, varias monedas"],
                    ["no", "No, una sola moneda"],
                  ] },
            ],
        },
        {
            type: "fields",
            question: "Inventario y productos",
            help: "Nos ayuda a dimensionar las necesidades de almacén y trazabilidad.",
            inputs: [
                { key: "x_diag_multi_location", kind: "select",
                  label: "Múltiples almacenes / ubicaciones", options: [
                    ["yes", "Sí, varias ubicaciones"],
                    ["no", "No, una sola ubicación"],
                  ] },
                { key: "x_diag_sku_range", kind: "select",
                  label: "Rango de productos / SKU", options: [
                    ["lt_100", "Menos de 100 SKU"],
                    ["100_1000", "De 100 a 1.000 SKU"],
                    ["1000_10000", "De 1.000 a 10.000 SKU"],
                    ["gt_10000", "Más de 10.000 SKU"],
                  ] },
                { key: "x_diag_variants", kind: "select",
                  label: "Variantes de producto (talla, color, etc.)", options: [
                    ["yes", "Sí, con variantes"],
                    ["no", "Sin variantes"],
                  ] },
                { key: "x_diag_traceability", kind: "select",
                  label: "Trazabilidad", options: [
                    ["none", "No necesita trazabilidad"],
                    ["serial", "Por número de serie"],
                    ["lot", "Por lote"],
                    ["both", "Por serie y lote"],
                  ] },
            ],
        },
        {
            type: "multi",
            required: false,
            question: "¿Qué integraciones necesitas?",
            help: "Selecciona todas las que apliquen (opcional).",
            cols: 2,
            options: [
                ["x_diag_int_shopify", "Shopify"],
                ["x_diag_int_woocommerce", "WooCommerce"],
                ["x_diag_int_payment_gateway", "Pasarela de pago"],
                ["x_diag_int_other", "Otra"],
            ],
            extra: { key: "x_diag_integration_notes", kind: "textarea",
                     label: "Detalle / frecuencia de la integración (opcional)" },
        },
        {
            type: "single",
            field: "x_diag_timeline",
            required: true,
            question: "¿Cuándo puede tu empresa empezar la implementación?",
            help: "Un proyecto exitoso necesita tiempo y compromiso de tu equipo.",
            cols: 2,
            options: [
                ["now", "Listo para empezar ya mismo"],
                ["1_2m", "Podemos empezar en 1-2 meses"],
                ["3_6m", "Todo en orden en 3-6 meses"],
                ["evaluating", "Aún evaluando, sin fecha definida"],
            ],
        },
        {
            type: "single",
            field: "x_diag_budget",
            required: true,
            question: "¿Cuál es tu presupuesto estimado para este proyecto?",
            help: "Las implementaciones de Odoo suelen ir de USD $5.000 a $25.000.",
            cols: 2,
            options: [
                ["5_10k", "USD $5.000 - $10.000"],
                ["10_15k", "USD $10.000 - $15.000"],
                ["15_25k", "USD $15.000 - $25.000"],
                ["not_sure", "Aún no lo sé"],
            ],
        },
        {
            type: "text",
            field: "x_diag_main_problem",
            required: true,
            question: "¿Cuál es el principal problema que quieres resolver con Odoo?",
            help: "Sé específico. Nos ayuda a entender tu situación antes de la llamada.",
            placeholder: "Describe tu principal desafío...",
        },
        {
            type: "contact",
            question: "Perfecto, ya casi terminamos.",
            help: "Déjanos tus datos y te contactaremos en 24-48 horas.",
        },
    ];

    // ----------------------------------------------------------------------
    // State
    // ----------------------------------------------------------------------
    var state = { index: 0, answers: {}, contact: {
        name: PREFILL.name, email: PREFILL.email,
        phone: PREFILL.phone, company: PREFILL.company,
    } };

    function esc(s) {
        return String(s == null ? "" : s)
            .replace(/&/g, "&amp;").replace(/</g, "&lt;")
            .replace(/>/g, "&gt;").replace(/"/g, "&quot;");
    }

    // ----------------------------------------------------------------------
    // Rendering
    // ----------------------------------------------------------------------
    function mount(html) { root.innerHTML = html; }

    function shell(inner, opts) {
        opts = opts || {};
        var total = STEPS.length;
        var pct = Math.round(((state.index) / total) * 100);
        var footer = "";
        if (opts.footer !== false) {
            footer =
                '<div class="diag-error" id="diag-error" style="display:none"></div>' +
                '<div class="diag-footer">' +
                  (state.index > 0
                    ? '<button type="button" class="diag-btn diag-btn-back" id="diag-back">&#8592; ATRÁS</button>'
                    : "") +
                  '<button type="button" class="diag-btn diag-btn-next" id="diag-next">' +
                      esc(opts.nextLabel || "SIGUIENTE") + " &#8594;</button>" +
                '</div>';
        }
        return (
            '<div class="diag-shell">' +
              '<div class="diag-brand">TICTEAMS</div>' +
              '<div class="diag-card">' +
                '<div class="diag-progress"><div class="diag-progress-bar" style="width:' + pct + '%"></div></div>' +
                '<div class="diag-body">' + inner + "</div>" +
                footer +
              "</div>" +
            "</div>"
        );
    }

    function header(step) {
        return (
            '<div class="diag-step-count">Paso ' + (state.index + 1) + " de " + STEPS.length + "</div>" +
            '<h2 class="diag-question">' + esc(step.question) + "</h2>" +
            (step.help ? '<p class="diag-help">' + esc(step.help) + "</p>" : "")
        );
    }

    function renderIntro() {
        mount(
            '<div class="diag-shell">' +
              '<div class="diag-brand">TICTEAMS<small>Implementación Odoo</small></div>' +
              '<div class="diag-card"><div class="diag-intro">' +
                "<h1>Cuéntanos sobre tu proyecto Odoo</h1>" +
                "<p>Responde unas preguntas sobre tu empresa y prepararemos una estimación " +
                "de costo y plazo a tu medida. Solo toma unos 3 minutos.</p>" +
                '<button type="button" class="diag-cta" id="diag-start">EMPEZAR &#8594;</button>' +
              "</div></div>" +
            "</div>"
        );
        document.getElementById("diag-start").onclick = function () {
            state.index = 0; renderStep();
        };
    }

    function optionCard(value, label, selected, multi) {
        return (
            '<div class="diag-option ' + (multi ? "multi " : "") +
                (selected ? "selected" : "") + '" data-value="' + esc(value) + '">' +
                '<span class="mark"></span>' + esc(label) +
            "</div>"
        );
    }

    function inputHtml(inp, val) {
        val = val == null ? "" : val;
        var req = inp.required ? ' <span class="req">*</span>' : "";
        var lbl = '<label>' + esc(inp.label) + req + "</label>";
        var ctrl;
        if (inp.kind === "textarea") {
            ctrl = '<textarea class="diag-textarea" data-key="' + esc(inp.key) + '">' + esc(val) + "</textarea>";
        } else if (inp.kind === "select") {
            var opts = '<option value="">— selecciona —</option>';
            inp.options.forEach(function (o) {
                opts += '<option value="' + esc(o[0]) + '"' +
                    (String(val) === o[0] ? " selected" : "") + ">" + esc(o[1]) + "</option>";
            });
            ctrl = '<select class="diag-input" data-key="' + esc(inp.key) + '">' + opts + "</select>";
        } else {
            var t = inp.kind === "number" ? "number" : "text";
            ctrl = '<input type="' + t + '" class="diag-input" data-key="' +
                esc(inp.key) + '" value="' + esc(val) + '"/>';
        }
        return '<div class="diag-field">' + lbl + ctrl + "</div>";
    }

    function renderStep() {
        var step = STEPS[state.index];
        if (!step) return;

        if (step.type === "contact") return renderContact(step);

        var inner = header(step);

        if (step.type === "single") {
            var cur = state.answers[step.field];
            inner += '<div class="diag-options cols-' + (step.cols || 2) + '" id="diag-opts">';
            step.options.forEach(function (o) {
                inner += optionCard(o[0], o[1], cur === o[0], false);
            });
            inner += "</div>";
        } else if (step.type === "multi") {
            inner += '<div class="diag-options cols-' + (step.cols || 2) + '" id="diag-opts">';
            step.options.forEach(function (o) {
                inner += optionCard(o[0], o[1], !!state.answers[o[0]], true);
            });
            inner += "</div>";
            if (step.extra) inner += '<div style="margin-top:18px">' +
                inputHtml(step.extra, state.answers[step.extra.key]) + "</div>";
        } else if (step.type === "text") {
            inner += '<textarea class="diag-textarea" id="diag-text" placeholder="' +
                esc(step.placeholder || "") + '">' +
                esc(state.answers[step.field] || "") + "</textarea>";
        } else if (step.type === "fields") {
            step.inputs.forEach(function (inp) {
                inner += inputHtml(inp, state.answers[inp.key]);
            });
        }

        mount(shell(inner, {}));
        bindNav();
        bindStepInputs(step);
    }

    function bindStepInputs(step) {
        if (step.type === "single") {
            Array.prototype.forEach.call(
                document.querySelectorAll("#diag-opts .diag-option"),
                function (el) {
                    el.onclick = function () {
                        state.answers[step.field] = el.getAttribute("data-value");
                        Array.prototype.forEach.call(
                            document.querySelectorAll("#diag-opts .diag-option"),
                            function (n) { n.classList.remove("selected"); });
                        el.classList.add("selected");
                        clearError();
                        // auto-advance for snappy single-choice steps
                        setTimeout(next, 180);
                    };
                });
        } else if (step.type === "multi") {
            Array.prototype.forEach.call(
                document.querySelectorAll("#diag-opts .diag-option"),
                function (el) {
                    el.onclick = function () {
                        var k = el.getAttribute("data-value");
                        state.answers[k] = !state.answers[k];
                        el.classList.toggle("selected", !!state.answers[k]);
                        clearError();
                    };
                });
        }
        bindFieldInputs();
    }

    function bindFieldInputs() {
        Array.prototype.forEach.call(
            document.querySelectorAll("[data-key]"),
            function (el) {
                el.oninput = el.onchange = function () {
                    state.answers[el.getAttribute("data-key")] = el.value;
                    clearError();
                };
            });
        var t = document.getElementById("diag-text");
        if (t) t.oninput = function () { clearError(); };
    }

    function renderContact(step) {
        var c = state.contact;
        var inner = header(step) +
            '<div class="diag-hp"><label>Deja esto vacío<input type="text" id="diag-hp"/></label></div>' +
            '<div class="diag-field"><label>Nombre <span class="req">*</span></label>' +
              '<input type="text" class="diag-input" id="c-name" value="' + esc(c.name) + '"/></div>' +
            '<div class="diag-field"><label>Correo <span class="req">*</span></label>' +
              '<input type="email" class="diag-input" id="c-email" value="' + esc(c.email) + '"/></div>' +
            '<div class="diag-field"><label>Teléfono</label>' +
              '<input type="text" class="diag-input" id="c-phone" value="' + esc(c.phone) + '"/></div>' +
            '<div class="diag-field"><label>Empresa</label>' +
              '<input type="text" class="diag-input" id="c-company" value="' + esc(c.company) + '"/></div>';
        mount(shell(inner, { nextLabel: "ENVIAR" }));
        bindNav();
    }

    function renderDone() {
        mount(
            '<div class="diag-shell">' +
              '<div class="diag-brand">TICTEAMS</div>' +
              '<div class="diag-card"><div class="diag-done">' +
                '<div class="diag-check"></div>' +
                "<h1>¡Gracias!</h1>" +
                "<p>Hemos recibido tu información. Nuestro equipo estudiará tu caso y " +
                "se pondrá en contacto contigo en las próximas 24-48 horas.</p>" +
              "</div></div>" +
            "</div>"
        );
    }

    // ----------------------------------------------------------------------
    // Navigation & validation
    // ----------------------------------------------------------------------
    function bindNav() {
        var b = document.getElementById("diag-back");
        var n = document.getElementById("diag-next");
        if (b) b.onclick = back;
        if (n) n.onclick = next;
    }

    function showError(msg) {
        var e = document.getElementById("diag-error");
        if (e) { e.textContent = msg; e.style.display = "block"; }
    }
    function clearError() {
        var e = document.getElementById("diag-error");
        if (e) e.style.display = "none";
    }

    function validate(step) {
        if (step.type === "single" && step.required) {
            if (!state.answers[step.field]) return "Por favor selecciona una opción.";
        } else if (step.type === "multi" && step.required) {
            var any = step.options.some(function (o) { return state.answers[o[0]]; });
            if (!any) return "Por favor selecciona al menos una opción.";
        } else if (step.type === "text" && step.required) {
            var v = (document.getElementById("diag-text") || {}).value || "";
            if (!v.trim()) return "Este campo es obligatorio.";
            state.answers[step.field] = v.trim();
        } else if (step.type === "fields") {
            for (var i = 0; i < step.inputs.length; i++) {
                var inp = step.inputs[i];
                if (inp.required && !(state.answers[inp.key] || "").toString().trim()) {
                    return "Por favor completa los campos obligatorios.";
                }
            }
        }
        return null;
    }

    function back() {
        clearError();
        if (state.index === 0) { renderIntro(); return; }
        state.index -= 1;
        renderStep();
    }

    function next() {
        var step = STEPS[state.index];
        if (step.type === "contact") return submit();
        var err = validate(step);
        if (err) { showError(err); return; }
        state.index += 1;
        renderStep();
    }

    // ----------------------------------------------------------------------
    // Submit
    // ----------------------------------------------------------------------
    function readContact() {
        state.contact = {
            name: (val("c-name")).trim(),
            email: (val("c-email")).trim(),
            phone: (val("c-phone")).trim(),
            company: (val("c-company")).trim(),
        };
    }
    function val(id) {
        var el = document.getElementById(id);
        return el ? el.value : "";
    }

    function submit() {
        readContact();
        var emailRe = /^[^@\s]+@[^@\s]+\.[^@\s]+$/;
        if (!state.contact.name) { showError("Por favor ingresa tu nombre."); return; }
        if (!emailRe.test(state.contact.email)) { showError("Por favor ingresa un correo válido."); return; }

        var btn = document.getElementById("diag-next");
        if (btn) { btn.disabled = true; btn.textContent = "Enviando..."; }

        var payload = {
            jsonrpc: "2.0",
            method: "call",
            params: {
                contact: state.contact,
                answers: state.answers,
                hp_field: val("diag-hp"),
            },
        };

        fetch("/odoo-diagnosis/submit", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(payload),
        })
        .then(function (r) { return r.json(); })
        .then(function (data) {
            var res = data && data.result;
            if (res && res.success) { renderDone(); }
            else {
                if (btn) { btn.disabled = false; btn.innerHTML = "ENVIAR &#8594;"; }
                showError("Algo salió mal. Revisa tus datos e inténtalo de nuevo.");
            }
        })
        .catch(function () {
            if (btn) { btn.disabled = false; btn.innerHTML = "ENVIAR &#8594;"; }
            showError("Error de red. Por favor inténtalo de nuevo.");
        });
    }

    // ----------------------------------------------------------------------
    // Boot
    // ----------------------------------------------------------------------
    renderIntro();
})();
