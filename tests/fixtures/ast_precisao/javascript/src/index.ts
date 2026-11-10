import React from 'react';
import './styles.css';
import data from './data.json';
import type { Tipo } from './types';
import { achado } from 'lib/fetcher';
export * from './api';
export { helper } from './lib/helpers';
export * as comps from './components';
// import { z } from './lib/fantasma';
/* export * from './lib/fantasma'; */
const fantasma = "import x from './lib/fantasma'";
const modelo = `require('./lib/fantasma')`;
export const v: Tipo = 1;
