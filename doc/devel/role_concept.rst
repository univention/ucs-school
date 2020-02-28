=================================================
UCS@school role concept for capability management
=================================================

In UCS@school we have the ucsschool roles to tag objects and map them to certain ucsschool types.
This feature will be extended to implement a capability management (rights system) to replace
the complex LDAP ACL structure and for delegating administrative work in a domain.

-------------------
Basic functionality
-------------------
In addition to the already existing role syntax of **role_name:context_type:context** so called
capabilities can be attached to roles. These capabilities are defined by Univention and represent
specific actions a user can perform. An example:

.. code-block::

    Capability: create_class_list
        name: ucsschool/create_class_list
        display_name: Klassenlisten erstellen
        description: This capability allows the role to create class lists of
                    any class in its school

This capability allows the user to list all students of any school class in his school.

There could now be a role called teacher this capability is attached to:

.. code-block::

    Role Teacher
        name: teacher
        display_name: Lehrer
        description: This role describes a teacher that can list the students of the classes
                    in his or her school.
        is_system_role: True
        capabilities: [ucsschool/create_class_list]

If the role would be attached to an actual user, it would be done by encoding the role
and its context in the ucsschool_roles attribute of the user object. If the user max.mustermann
is supposed to be a teacher at the school *School1*, the ucsschool role string to be attached would be:

    teacher:school:School1

With previous definitions this would mean that max.mustermann can list all classes of School1, but no
other school. The role string represents a contextualized role and binds the capabilities
attached to the role to the specified context. In this case, a school.

--------------
Targeted Roles
--------------

Some capabilities can be restricted in a way that they only apply if the target has a certain role.
In the previous example the teacher could be expanded to be able to reset the password of students.
To represent this in the UCS@school role concept a new capability is necessary:

.. code-block::

    Capability: reset_password
        name: ucsschool/reset_password
        display_name: Passwort zurücksetzen
        description: This capability allows the role to reset the password of all users in its
                    school. This is a targeted capability and can be restricted to a specific role.

This capability is targeted and thus its scope can be restricted not only to a context
(implicit by the context of the role), but also to a specific role. For that the target has to be
encoded in the role object by adding the target role to the capability string in the role definition.
In the case of the teacher the role object would be extended like this:

.. code-block::

    Role Teacher
        name: teacher
        display_name: Lehrer
        description: This role describes a teacher that can list the students of the classes
                    in his or her school.
        is_system_role: True
        capabilities: [ucsschool/create_class_list, ucsschool/reset_password student]

The added capability string *ucsschool/reset_password student* adds the capability to reset passwords
to the teacher role, but this capability is restricted to objects of the role student only.
To give the teacher the ability to reset the passwords of student and parent roles a second
capability string would be added: *ucsschool/reset_password parent*.

It is important to note that in the specific instance of max.mustermann he could only reset
the password of students of the School1, thus the restraints of context **and** target have to be
fullfilled for a capability to be verified.