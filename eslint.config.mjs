import tseslint from "typescript-eslint";

export default tseslint.config({
    files: ["app/frontend/src/**/*.ts"],
    extends: [tseslint.configs.strictTypeChecked],
    rules: {
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
