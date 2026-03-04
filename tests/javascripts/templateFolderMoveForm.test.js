const helpers = require("./support/helpers");

function setFixtures(hierarchy, newTemplateDataModules = "") {
  const foldersCheckboxesHTML = (function (filter) {
    let count = 0;

    // use closure to give all calls access to count
    return function (nodes) {
      let result = "";

      nodes
        .filter((node) => node.type === "folder")
        .forEach((node) => {
          result += `<li class="multiple-choice">
                      <input id="node-${count}" name="move_to" type="radio" value="node-${count}">
                      <label class="block-label" for="node-${count}">
                        ${node.label}
                      </label>
                      ${
                        node.children
                          ? foldersCheckboxesHTML(node.children)
                          : ""
                      }
                    </li>`;
          count++;
        });

      return `<ul>${result}</ul>`;
    };
  })();

  function controlsHTML(newTemplateDataModules) {
    return `<div id="sticky_template_forms">
              <button name="operation" value="unknown" hidden=""></button>
              <input type="hidden" name="csrf_token" value="ImY1NTNlMGY1N2VkMjE3M2VmMzJhYjA4NDZjNzAwOWI4MjQ4MmI0YmEi.Y2ulgg.bNsKybu2SPmQ5FB7Zb4A1et8oHw">
              <input type="hidden" name="template_folders_to_move" value="[]">
              <div id="move_to_folder_radios" class="sticky-template-form" role="region" aria-label="Choose the location you want to move your template or folder to">
                <div class="form-group ">
                  <fieldset id="move_to">
                    <legend class="form-label">
                      Choose the location you want to move your template or folder to
                    </legend>
                    <div class="radios-nested">
                      ${foldersCheckboxesHTML(hierarchy)}
                    </div>
                  </fieldset>
                </div>
                <div class="js-will-stick-at-bottom-when-scrolling">
                  <button class="govuk-button page-footer__button" name="operation" value="move-to-existing-folder" data-module="govuk-button">Move</button>
                  <a href="" class="govuk-link govuk-link--no-visited-state js-cancel" tabindex="0">Cancel<span class="govuk-visually-hidden"> move to operation</span></a>
                </div>
              </div>`;
  }

  document.body.innerHTML = `
    <form method="post" data-notify-module="template-folder-move-form">
      ${controlsHTML(newTemplateDataModules)}
    </form>`;
}

function resetStickyMocks() {
  GOVUK.stickAtBottomWhenScrolling.recalculate.mockClear();
  GOVUK.stickAtBottomWhenScrolling.setMode.mockClear();
}

beforeAll(() => {
  require("../../app/assets/javascripts/templateFolderMoveForm.js");

  // plug JSDOM's lack of support for window.scrollTo
  window.scrollTo = () => {};
});

afterAll(() => {
  require("./support/teardown.js");

  // tidy up
  delete window.scrollTo;
});

describe("TemplateFolderMoveForm", () => {
  const hierarchy = [
    {
      label: "Folder 1",
      type: "folder",
      meta: "1 template, 1 folder",
      children: [
        {
          label: "Template 3",
          type: "template",
          meta: "Email template",
        },
        {
          label: "Folder 2",
          type: "folder",
          meta: "Empty",
          children: [],
        },
      ],
    },
    {
      label: "Folder 3",
      type: "folder",
      meta: "Empty",
    },
    {
      label: "Template 2",
      type: "template",
      meta: "Email template",
    },
  ];

  let templateFolderMoveForm;
  let formControls;

  beforeAll(() => {
    // stub out calls to sticky JS
    GOVUK.stickAtBottomWhenScrolling = {
      setMode: jest.fn(),
      recalculate: jest.fn(),
    };
  });

  afterAll(() => {
    GOVUK.stickAtBottomWhenScrolling = undefined;
  });

  beforeEach(() => {
    setFixtures(hierarchy);

    templateFolderMoveForm = document.querySelector(
      "form[data-notify-module=template-folder-move-form]"
    );
    console.log(templateFolderMoveForm.innerHTML);
  });

  afterEach(() => {
    document.body.innerHTML = "";
  });


  describe("Before the module starts", () => {
    // We need parts of the module to be made sticky, but by the module code,
    // not the sticky JS code that operates on the HTML at page load.
    // Because of this, they will need to be marked with classes
    test("the HTML for the module should contain placeholder classes on each part that needs to be sticky", () => {
      expect(
        templateFolderMoveForm.querySelectorAll(
          "#sticky_template_forms .js-will-stick-at-bottom-when-scrolling"
        ).length
      ).toEqual(1);
    });
  });

  describe("When the module starts", () => {
    beforeEach(() => {
      // start module
      window.GOVUK.notifyModules.start();

      formControls = templateFolderMoveForm.querySelector("#sticky_template_forms");
      console.log(formControls.innerHTML);
    });

    afterEach(() => resetStickyMocks());

    test("the default controls should be showing", () => {
      expect(
        formControls.querySelector("button[value=move-to-existing-folder]")
      ).not.toBeNull();
      expect(
        formControls.querySelector(".js-cancel")
      ).not.toBeNull();
    });

    test("Check the 'Cancel' link", () => {
      const cancelLink = formControls.querySelector(".js-cancel");
      expect(cancelLink).not.toBeNull();
      expect(
        cancelLink.querySelector(".govuk-visually-hidden")
      ).not.toBeNull();
      expect(
        cancelLink
          .querySelector(".govuk-visually-hidden")
          .textContent.trim()
      ).toEqual("move to operation");
    });

    test("should make the current controls sticky", () => {
      // the class the sticky JS hooks into should be present
        expect(
          formControls.querySelector(
            "#sticky_template_forms .js-stick-at-bottom-when-scrolling"
          )
        ).not.toBeNull();

        console.log(
           formControls.querySelector(
            "#sticky_template_forms .js-stick-at-bottom-when-scrolling"
          ).innerHTML
        )

        // .recalculate should have been called so the sticky JS picks up the controls
        expect(
          GOVUK.stickAtBottomWhenScrolling.recalculate.mock.calls.length
        ).toEqual(1);

        // mode should have been set to 'default' as the controls only have one part
        expect(
          GOVUK.stickAtBottomWhenScrolling.setMode.mock.calls.length
        ).toEqual(1);
        expect(
          GOVUK.stickAtBottomWhenScrolling.setMode.mock.calls[0][0]
        ).toEqual("default");
      });


  });

});
