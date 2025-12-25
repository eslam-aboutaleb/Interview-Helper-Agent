// This file contains custom TypeScript declarations
// for modules that might be missing type definitions

declare module 'react';
declare module 'react-dom';
declare module 'react-router-dom';
declare module 'react-hot-toast';

// Add JSX runtime declarations
declare module 'react/jsx-runtime';
declare module 'react/jsx-dev-runtime';

// Add JSX IntrinsicElements interface
declare namespace JSX {
  interface IntrinsicElements {
    div: any;
    main: any;
    nav: any;
    header: any;
    a: any;
    button: any;
    span: any;
    h1: any;
    h2: any;
    h3: any;
    h4: any;
    h5: any;
    h6: any;
    p: any;
    form: any;
    input: any;
    textarea: any;
    select: any;
    option: any;
    label: any;
    ul: any;
    ol: any;
    li: any;
    table: any;
    tr: any;
    td: any;
    th: any;
    section: any;
    img: any;
    svg: any;
    path: any;
    [elemName: string]: any;
  }
}
