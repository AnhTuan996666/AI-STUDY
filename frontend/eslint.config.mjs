import coreWebVitals from 'eslint-config-next/core-web-vitals';
import typescriptConfig from 'eslint-config-next/typescript';

/** Flat config — eslint-config-next 16 đã xuất sẵn dạng flat, không cần FlatCompat. */
const eslintConfig = [
  ...coreWebVitals,
  ...typescriptConfig,
  {
    ignores: ['.next/**', 'node_modules/**', 'next-env.d.ts'],
  },
];

export default eslintConfig;
