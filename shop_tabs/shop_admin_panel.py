        # --- BRANCH MANAGEMENT SECTION ---
        st.markdown("#### 🌿 Shop Branches")
        with st.form("branch_add_form"):
            new_branch_name = st.text_input("Add New Branch / Counter Name")
            add_b_btn = st.form_submit_button("Add Branch")
            if add_b_btn:
                if new_branch_name.strip():
                    b_s, b_m = database.add_shop_branch(current_shop_user, new_branch_name)
                    if b_s:
                        st.success(b_m)
                        st.rerun()
                    else:
                        st.error(b_m)
                else:
                    st.warning("Please enter a branch name.")
                    
        # Fetch existing branches for dropdown selection
        branches_data = database.fetch_shop_branches(current_shop_user)
        branch_options = [b['branch_name'] for b in branches_data] if branches_data else ["Main Branch"]

        st.markdown("---")
        st.markdown("#### 👥 Staff Sub-Accounts & PIN Access")
        
        # Staff Registration Form (Using clear inputs via Session State or standard rerun)
        with st.form("staff_sub_form"):
            col_s1, col_s2 = st.columns(2)
            with col_s1:
                staff_name = st.text_input("Staff Name", value="")
                # PIN එක password ලෙස නැතුව සාමාන්‍ය අංකයක් ලෙස පෙන්වීමට text_input (max_chars 6) පාවිච්චි කළ හැක
                staff_pin = st.text_input("Staff PIN (e.g. 1234)", value="", max_chars=6, help="Enter 4 to 6 digit PIN")
            with col_s2:
                role = st.selectbox("Staff Role", ["Cashier", "Stock Inventory Manager"])
                # දැන් අතින් ටයිප් කිරීම වෙනුවට ඩේටාබේස් එකේ ඇති බ්‍රාන්ච් ලැයිස්තුවෙන් නිවැරදිව select කරගත හැක
                branch_name = st.selectbox("Assign to Branch", options=branch_options)
                
            add_staff_btn = st.form_submit_button("Add Staff Sub-Account")
            
            if add_staff_btn:
                if staff_name.strip() and staff_pin.strip():
                    s_succ, s_msg = database.add_shop_staff(current_shop_user, staff_name, staff_pin, role, branch_name)
                    if s_succ:
                        st.success(s_msg)
                        st.rerun() # බටන් එක ක්ලික් කළ පසු ස්ටේට් එක රීෆ්‍රෙශ් වී ඩේටා ඉන්පුට් ෆීල්ඩ්ස් ක්ලියර් වේ
                    else:
                        st.error(s_msg)
                else:
                    st.warning("Please fill in staff name and PIN.")

        # Show Staff List with Delete confirmation
        staff_list = database.fetch_shop_staff(current_shop_user)
        if staff_list:
            st.markdown("##### Existing Staff Members")
            df_staff = pd.DataFrame(staff_list)[['staff_name', 'role', 'branch_name', 'created_at']]
            st.dataframe(df_staff, use_container_width=True)
            
            selected_to_del = st.selectbox("Select Staff to Delete", options=staff_list, format_func=lambda x: f"{x['staff_name']} ({x['role']} - {x['branch_name']})", key="del_staff_box")
            if st.button("Delete Selected Staff"):
                st.session_state["confirm_del_staff"] = True
                
            if st.session_state.get("confirm_del_staff", False):
                st.warning(f"Are you sure you want to delete staff member: **{selected_to_del['staff_name']}**?")
                c_y, c_n = st.columns(2)
                with c_y:
                    if st.button("Yes, Delete"):
                        database.delete_shop_staff(selected_to_del['id'])
                        st.session_state["confirm_del_staff"] = False
                        st.success("Staff deleted successfully!")
                        st.rerun()
                with c_n:
                    if st.button("Cancel"):
                        st.session_state["confirm_del_staff"] = False
                        st.rerun()
        else:
            st.info("No staff sub-accounts created yet.")