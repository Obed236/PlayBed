(() => {
    function decodeLegacyString(value) {
        return value
            .replace(/\\(['"\\])/g, "$1")
            .replace(/\\n/g, "\n")
            .replace(/\\r/g, "\r")
            .replace(/\\t/g, "\t");
    }

    function migrateConfirmForm(form) {
        if (!(form instanceof HTMLFormElement)) return null;
        if (form.dataset.cspConfirm) return form.dataset.cspConfirm;

        const source = form.getAttribute("onsubmit") || "";
        const match = source.match(
            /^\s*return\s+confirm\(\s*(['"])([\s\S]*)\1\s*\)\s*;?\s*$/
        );
        if (!match) return null;

        const message = decodeLegacyString(match[2]);
        form.dataset.cspConfirm = message;
        form.removeAttribute("onsubmit");
        return message;
    }

    function migrateCopyButton(button) {
        if (!(button instanceof HTMLButtonElement)) return null;
        if (button.dataset.cspCopyTarget) return button.dataset.cspCopyTarget;

        const source = button.getAttribute("onclick") || "";
        const match = source.match(
            /navigator\.clipboard\.writeText\(\s*document\.getElementById\(\s*['"]([^'"]+)['"]\s*\)\.value\s*\)/
        );
        if (!match) return null;

        button.dataset.cspCopyTarget = match[1];
        button.removeAttribute("onclick");
        return match[1];
    }

    function migrateLegacyHandlers(root = document) {
        root.querySelectorAll("form[onsubmit]").forEach(migrateConfirmForm);
        root.querySelectorAll("button[onclick]").forEach(migrateCopyButton);
    }

    if (document.readyState === "loading") {
        document.addEventListener("DOMContentLoaded", () => migrateLegacyHandlers());
    } else {
        migrateLegacyHandlers();
    }

    document.addEventListener(
        "submit",
        (event) => {
            const form = event.target;
            const message = migrateConfirmForm(form);
            if (message === null) return;

            if (!window.confirm(message)) {
                event.preventDefault();
                event.stopImmediatePropagation();
            }
        },
        true
    );

    document.addEventListener(
        "click",
        async (event) => {
            const target = event.target;
            if (!(target instanceof Element)) return;

            const button = target.closest("button[data-csp-copy-target], button[onclick]");
            if (!button) return;

            const targetId = migrateCopyButton(button);
            if (!targetId) return;

            const source = document.getElementById(targetId);
            if (!source) return;

            event.preventDefault();

            const text = "value" in source ? source.value : source.textContent || "";
            try {
                await navigator.clipboard.writeText(text);
                button.textContent = "Copié ✓";
            } catch {
                if (typeof source.focus === "function") source.focus();
                if (typeof source.select === "function") source.select();
                try {
                    document.execCommand("copy");
                    button.textContent = "Copié ✓";
                } catch {
                    button.textContent = "Copie impossible";
                }
            }
        },
        true
    );
})();
