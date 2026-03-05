const helpers = require("./support/helpers");

function setFixtures(hierarchy, current_folder_id = 'None', folders_to_move = null) {
  const foldersCheckboxesHTML = (function (filter, offset = 0) {
    let count = 0;

    // use closure to give all calls access to count
    return function (nodes) {
      let result = "";

      nodes
        .filter((node) => node.type === "folder")
        .forEach((node) => {
          result += `<li class="multiple-choice">
                      <input id="node-${count}-${offset}" name="move_to" type="radio" value="node-${count}-${offset}">
                      <label class="block-label" for="node-${count}-${offset}">
                        ${node.label}
                      </label>
                      ${
                        node.children
                          ? foldersCheckboxesHTML(node.children, offset++)
                          : ""
                      }
                    </li>`;
          count++;
        });
      return `<ul>${result}</ul>`;
    };
  })();

  function wrapRadios(radioList) {
    // add parent 'Templates' hierarchy
    radioList = `
          <ul><li class="multiple-choice">
          <input id="node-x" name="move_to" type="radio" value="__NONE__">
          <label class="block-label" for="node-x">
            Templates
          </label>
          ` + radioList + `
          </li></ul>
        `;
    return radioList;
  }

  function controlsHTML() {
    return `<div id="sticky_template_forms">
              <button name="operation" value="unknown" hidden=""></button>
              <input type="hidden" name="csrf_token" value="ImY1NTNlMGY1N2VkMjE3M2VmMzJhYjA4NDZjNzAwOWI4MjQ4MmI0YmEi.Y2ulgg.bNsKybu2SPmQ5FB7Zb4A1et8oHw">
              <input type="hidden" name="template_folders_to_move" value="[${folders_to_move}]">
              <input type="hidden" name="current_folder_id" value="${current_folder_id}">
              <div id="move_to_folder_radios" class="sticky-template-form" role="region" aria-label="Choose the location you want to move your template or folder to">
                <div class="form-group ">
                  <fieldset id="move_to">
                    <legend class="form-label">
                      Choose the location you want to move your template or folder to
                    </legend>
                    <div class="radios-nested">
                      ${wrapRadios(foldersCheckboxesHTML(hierarchy))}
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
      ${controlsHTML()}
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
    setFixtures(hierarchy, "None");

    templateFolderMoveForm = document.querySelector(
      "form[data-notify-module=template-folder-move-form]"
    );
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
      //TODO cancel link href should match back link href
    });

    test("should make the current controls sticky", () => {
      // the class the sticky JS hooks into should be present
        expect(
          formControls.querySelector(
            "#sticky_template_forms .js-stick-at-bottom-when-scrolling"
          )
        ).not.toBeNull();

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

  describe("When folder list is displayed", () => {

    afterEach(() => resetStickyMocks());

    test("top level radio button is disabled with comment if current_folder_id is None", () => {

      setFixtures(hierarchy, "None");

      //initialise module
      window.GOVUK.notifyModules.start();

      templateFolderMoveForm = document.querySelector(
        "form[data-notify-module=template-folder-move-form]"
      );

      expect(
        templateFolderMoveForm.querySelector('#node-x')
      ).not.toBeNull;
      expect(
        templateFolderMoveForm.querySelector('#node-x').getAttribute("disabled")
      ).toEqual(""); //i.e. not null
      expect(
        templateFolderMoveForm.querySelector('label[for="node-x"]')
      ).not.toBeNull;
      expect(
        templateFolderMoveForm.querySelector('label[for="node-x"]').textContent.trim()
      ).toContain("Templates");
      expect(
        templateFolderMoveForm.querySelector('label[for="node-x"]').textContent.trim()
      ).toContain("<-- current location");
    });

    test("radio button is disabled with comment if current_folder_id not None", () => {

      setFixtures(hierarchy, "node-2-2");

      //initialise module
      window.GOVUK.notifyModules.start();

      templateFolderMoveForm = document.querySelector(
        "form[data-notify-module=template-folder-move-form]"
      );

      expect(
        templateFolderMoveForm.querySelector('#node-2-2')
      ).not.toBeNull;
      expect(
        templateFolderMoveForm.querySelector('#node-2-2').getAttribute("disabled")
      ).toEqual(""); //i.e. not null
      expect(
        templateFolderMoveForm.querySelector('label[for="node-2-2"]')
      ).not.toBeNull;
      expect(
        templateFolderMoveForm.querySelector('label[for="node-2-2"]').textContent.trim()
      ).toContain("Folder 3");
      expect(
        templateFolderMoveForm.querySelector('label[for="node-2-2"]').textContent.trim()
      ).toContain("<-- current location");
    });

    test("folder to be removed and any sub folders are removed from folder list", () => {
      setFixtures(hierarchy, "None", "'node-0-0'" );

      //initialise module
      window.GOVUK.notifyModules.start();

      templateFolderMoveForm = document.querySelector(
        "form[data-notify-module=template-folder-move-form]"
      );

      expect(
        templateFolderMoveForm.querySelector('#node-0-0')
      ).toBeNull;
      expect(
        templateFolderMoveForm.querySelector('#node-0-1')
      ).toBeNull;
      expect(
        templateFolderMoveForm.querySelector('#node-2-2')
      ).not.toBeNull;
    });

  });

});
