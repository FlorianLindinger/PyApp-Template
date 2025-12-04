# Composite License File

This repository contains components under separate licenses as described in the sections below.

---

## Section 1: Notice on File Distribution

This repository may contain, after execution of any of its codes, newly generated files of the **Python distribution** or **third-party Python packages**. These files are not part of the project’s original source code and are **not necessarily allowed to be distributed** under their respective licenses (see Sections 4 and 5 below). **If you distribute this repository, you must**:

1. Ensure the main licenses described in Section 2 and 3 allow for your way of distribution
2. - When distributing via Git:
   If the files in `code/do_not_change` are unaltered, `.gitignore` files are added which auto-exclude files licensed as described in Sections 4 and 5 from distribution via git. If you alter anything in `code/do_not_change`, make sure this behavior does not change and/or alter this license file accordingly.
   - When distributing by any other method:
   Ensure that the licenses described in Sections 4 and 5 allow for your mode of distribution.

---

## Section 2: Main Project - License

All files in this repository, **except for files in the folders described in Sections 3,4, and 5**, are governed by the following license:

```
[Insert your chosen license text here]
```

---

## Section 3: Original Template - License (Composite License)

This App is based on the template from https://github.com/FlorianLindinger/PyApp-Template by Florian Lindinger. This backend code is located in the **`code/do_not_change`** folder and falls under the composite license described in the `LICENSE.md` file within that folder.

---

## Section 4: Python Distribution & Virtual Environment - License (likely PSF License)

Files inside the folders **`code/py_env/virt_env`** (**except for the folder described in Section 5**) and **`code/py_env/py_dist`** fall under the license of the *Python Software Foundation*, which is usually included as the `LICENSE.txt` file in the latter folder.

---

## Section 5: Third-Party Python Package - Licenses

Files inside **`code/py_env/virt_env/Lib/site-packages`** are third-party Python packages that fall under their respective licenses, which are usually included in their respective folders.

---