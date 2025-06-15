module.exports = {
    env: {
      browser: true,
      es2021: true,
    },
    extends: [
      'eslint:recommended',
      'plugin:react/recommended',
      'plugin:jsx-a11y/recommended',
      'prettier',
    ],
    plugins: ['react', 'react-hooks', 'jsx-a11y'],
    parserOptions: {
      ecmaVersion: 'latest',
      sourceType: 'module',
      ecmaFeatures: {
        jsx: true,
      },
    },
    rules: {
      'react/react-in-jsx-scope': 'off', // plus nécessaire avec Vite
    },
    settings: {
      react: {
        version: 'detect',
      },
    },
  }
  