import { nodeResolve } from '@rollup/plugin-node-resolve';
import multi from '@rollup/plugin-multi-entry';
import terser from '@rollup/plugin-terser';
import copy from 'rollup-plugin-copy';
import styles from "rollup-plugin-styler";

const paths = {
  src: 'app/assets/',
  dist: 'app/static/',
  npm: 'node_modules/',
  govuk_frontend: 'node_modules/govuk-frontend/dist/'
};

export default [
  // ESM compilation and copy static assets
  {
    input: paths.src + 'javascripts/esm/all.mjs',
    output: {
      dir: paths.dist + 'javascripts/',
      entryFileNames: 'all.mjs',
      // We're using an IIFE because currently, a lot of our JavaScript accesses dependencies from the
      // window.GOVUK namespace. The modern approach would be to refactor to modules. But for now,
      // to ensure there isn't a race condition between `all.mjs` (which does the exports the rest of
      // the JavaScripts need), we use an IIFE and pull it into our base template.
      format: 'iife',
      name: 'GOVUK'
    },
    plugins: [
      nodeResolve(),
      terser(),
      // copy images, error pages and govuk-frontend static assets
      copy({
        targets: [
          { src: paths.src + 'error_pages/**/*', dest: paths.dist + 'error_pages/' },
          { src: [ paths.src + 'images/**/*', paths.govuk_frontend + 'govuk/assets/images/**/*' ], dest: paths.dist + 'images/' },
          { src: paths.govuk_frontend + 'govuk/assets/fonts/**/*', dest: paths.dist + 'fonts/' },
          { src: paths.govuk_frontend + 'govuk/assets/manifest.json', dest: paths.dist },
          { src: paths.src + 'metadata/**/*', dest: paths.dist + 'metadata/' },
        ]
      })
    ]
  },
  // SCSS compilation
  {
    input: [
      paths.src + 'stylesheets/main.scss',
      paths.src + 'stylesheets/print.scss',
      paths.src + 'stylesheets/map.scss'
    ],
    output: {
      dir: paths.dist + 'stylesheets/',
      assetFileNames: "[name][extname]",
    },
    plugins: [
      // https://anidetrix.github.io/rollup-plugin-styles/interfaces/types.Options.html
      styles({
        mode: "extract",
        sass: {
          includePaths: [
            paths.govuk_frontend,
            paths.npm
          ],
        },
        minimize: true,
        url: false,
      }),
    ]
  },
  // ES5 JS compilation
  {
    input: [
      paths.npm + 'hogan.js/dist/hogan-3.0.2.js',
      paths.npm + 'jquery/dist/jquery.min.js',
      paths.npm + 'query-command-supported/dist/queryCommandSupported.min.js',
      paths.npm + 'timeago/jquery.timeago.js',
      paths.npm + 'textarea-caret/index.js',
      paths.npm + 'cbor-js/cbor.js',
      paths.src + 'javascripts/modules.js',
      paths.src + 'javascripts/govuk-frontend-toolkit/show-hide-content.js',
      paths.src + 'javascripts/govuk/cookie-functions.js',
      paths.src + 'javascripts/consent.js',
      paths.src + 'javascripts/analytics/analytics.js',
      paths.src + 'javascripts/analytics/init.js',
      paths.src + 'javascripts/cookieMessage.js',
      paths.src + 'javascripts/cookieSettings.js',
      paths.src + 'javascripts/stick-to-window-when-scrolling.js',
      paths.src + 'javascripts/copyToClipboard.js',
      paths.src + 'javascripts/autofocus.js',
      paths.src + 'javascripts/enhancedTextbox.js',
      paths.src + 'javascripts/fileUpload.js',
      paths.src + 'javascripts/radioSelect.js',
      paths.src + 'javascripts/updateContent.js',
      paths.src + 'javascripts/listEntry.js',
      paths.src + 'javascripts/liveSearch.js',
      paths.src + 'javascripts/errorTracking.js',
      paths.src + 'javascripts/preventDuplicateFormSubmissions.js',
      paths.src + 'javascripts/fullscreenTable.js',
      paths.src + 'javascripts/radios-with-images.js',
      paths.src + 'javascripts/previewPane.js',
      paths.src + 'javascripts/colourPreview.js',
      paths.src + 'javascripts/templateFolderForm.js',
      paths.src + 'javascripts/addBrandingOptionsForm.js',
      paths.src + 'javascripts/collapsibleCheckboxes.js',
      paths.src + 'javascripts/registerSecurityKey.js',
      paths.src + 'javascripts/authenticateSecurityKey.js',
      paths.src + 'javascripts/updateStatus.js',
      paths.src + 'javascripts/errorBanner.js',
      paths.src + 'javascripts/homepage.js',
      paths.src + 'javascripts/main.js',
      paths.src + 'javascripts/sessionTimeout.js',
      paths.src + 'javascripts/exclusiveCheckbox.js',
      paths.src + 'javascripts/permissionFormSubmitButton.js',
      paths.src + 'javascripts/selectAllCheckboxes.js',
      paths.src + 'javascripts/discardDraftAlerts.js',
      paths.src + 'javascripts/recalculateStickinessOnMutation.js',
    ],
    output: {
      dir: paths.dist + 'javascripts/',
    },
    moduleContext: {
      './node_modules/jquery/dist/jquery.min.js': 'window',
      './node_modules/cbor-js/cbor.js': 'window',
    },
    plugins: [
      nodeResolve(),
      multi({
        entryFileName: 'all.js'
      }),
      terser({
        ecma: '5',
        mangle: {
          reserved: ["Hogan"]
        }
      })
    ]
  },
  // JavaScripts that do not go in the bundled all.js
  {
    input: [
      paths.npm + 'leaflet/dist/leaflet.js',
    ],
    output: {
      dir: paths.dist + 'javascripts/',
    },
    moduleContext: {
      './node_modules/leaflet/dist/leaflet.js': 'window',
    },
    plugins: [
      nodeResolve(),
      multi({
        entryFileName: 'leaflet.js'
      }),
      terser({
        ecma: '5',
        mangle: {
          reserved: ["Hogan"]
        }
      }),
    ]
  },
  {
    input: [
      paths.npm + 'proj4/dist/proj4.js',
    ],
    output: {
      dir: paths.dist + 'javascripts/',
    },
    moduleContext: {
      './node_modules/proj4/dist/proj4.js': 'window',
    },
    plugins: [
      nodeResolve(),
      multi({
        entryFileName: 'proj4.js'
      }),
      terser({
        ecma: '5',
        mangle: {
          reserved: ["Hogan"]
        }
      }),
    ]
  },
  {
    input: [
      paths.src + 'javascripts/esm/customMapping.mjs',
    ],
    output: {
      dir: paths.dist + 'javascripts/',
      format: "es",
      entryFileNames: "customMapping.mjs"
    },
    plugins: [
      nodeResolve(),
      terser({
        mangle: {
          reserved: ["Hogan"]
        }
      }),
    ]
  }
];
