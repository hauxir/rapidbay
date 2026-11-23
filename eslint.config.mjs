import tseslint from "typescript-eslint";

export default tseslint.config({
    files: ["app/frontend/src/**/*.ts"],
    extends: [tseslint.configs.strictTypeChecked],
    linterOptions: {
        reportUnusedDisableDirectives: "error",
    },
    rules: {
        // No `any`, written or inherited: these are already in
        // strictTypeChecked, listed so the policy doesn't hinge on the preset.
        "@typescript-eslint/no-explicit-any": ["error", { fixToUnknown: false, ignoreRestArgs: false }],
        "@typescript-eslint/no-unsafe-argument": "error",
        "@typescript-eslint/no-unsafe-assignment": "error",
        "@typescript-eslint/no-unsafe-call": "error",
        "@typescript-eslint/no-unsafe-member-access": "error",
        "@typescript-eslint/no-unsafe-return": "error",
        // Style rules, not type safety. The code keeps its original ES5
        // idiom (function-scoped var, `var self = this` in callbacks).
        "no-var": "off",
        "@typescript-eslint/no-this-alias": "off",
    },
    languageOptions: {
        parserOptions: {
            projectService: true,
            tsconfigRootDir: import.meta.dirname,
        },
    },
});
