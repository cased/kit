module.exports = {
  root: true,
  parser: "@typescript-eslint/parser",
  plugins: ["@typescript-eslint"],
  extends: ["eslint:recommended", "plugin:@typescript-eslint/recommended"],
  env: {
    es2021: true,
    node: true,
    jest: true,
  },
  ignorePatterns: ["dist/", "node_modules/"],
  rules: {
    "@typescript-eslint/no-explicit-any": "off",
    "@typescript-eslint/no-unused-vars": ["warn", { argsIgnorePattern: "^_" }],
    "@typescript-eslint/ban-types": [
      "warn",
      {
        types: {
          Symbol: false,
        },
        extendDefaults: true,
      },
    ],
    "@typescript-eslint/no-var-requires": "off",
    "no-empty": ["warn", { allowEmptyCatch: true }],
  },
};
