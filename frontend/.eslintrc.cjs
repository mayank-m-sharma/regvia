module.exports = {
  root: true,
  env: { browser: true, es2020: true },
  extends: [
    'airbnb',
    'airbnb-typescript',
    'airbnb/hooks',
    'plugin:@typescript-eslint/recommended-type-checked',
    'plugin:jsx-a11y/recommended',
  ],
  ignorePatterns: [
    'dist',
    'coverage',
    '.eslintrc.cjs',
    'vite.config.ts',
    'vitest.config.ts',
    'postcss.config.js',
    'tailwind.config.js',
  ],
  parser: '@typescript-eslint/parser',
  parserOptions: {
    ecmaVersion: 'latest',
    sourceType: 'module',
    project: ['./tsconfig.json'],
    tsconfigRootDir: __dirname,
  },
  rules: {
    'react/react-in-jsx-scope': 'off',
    'import/extensions': 'off',
    'import/prefer-default-export': 'off',
    'react/require-default-props': 'off',
    'react/jsx-no-bind': 'off',
    'react/jsx-props-no-spreading': 'off',
  },
  overrides: [
    {
      // Test files: relax rules that don't apply in a test context
      files: ['src/test/**/*.{ts,tsx}', 'src/**/*.test.{ts,tsx}'],
      rules: {
        'import/no-extraneous-dependencies': ['error', { devDependencies: true }],
        'import/prefer-default-export': 'off',
        'react/require-default-props': 'off',
        'no-console': 'off',
      },
    },
  ],
};
